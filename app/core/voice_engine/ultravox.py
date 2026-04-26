"""
Ultravox Voice Engine adapter.
Translates between unified schema ↔ Ultravox wire protocol.
"""
import json
import os
from typing import AsyncGenerator
import websockets
from .base import BaseVoiceEngine
from app.config.env import Env
from app.utils.logger import logger
from app.utils.http.client import Client
from ..schemas.unified import (
    AgentResponse, AgentState, AudioChunk, AudioResponse, ContextUpdate,
    ErrorMessage, HangUp, Ping, Pong, SessionConfig, SessionReady,
    StateUpdate, Transcript, TranscriptRole, ToolCall, ToolResult,
    UnifiedMessage, UserText, VoiceEngine, MessageType,
)
import base64
import audioop


class UltravoxVoiceEngine(BaseVoiceEngine):
    @property
    def name(self) -> str:
        return "ultravox"

    def __init__(self) -> None:
        self.api_key = Env.ULTRAVOX_API_KEY
        if self.api_key is None:
            raise Exception("ULTRAVOX_API_KEY is not set")
        self.http_client = Client("https://api.ultravox.ai")
        self._ws: websockets.ClientConnection | None = None

    async def connect(self, config: SessionConfig) -> None:
        try:
            if config.agent is None:
                raise Exception("Agent Config is not set")
            agent_config = config.agent

            if agent_config.agent_id is None:
                raise Exception("Agent ID is not set")
            agent_id = agent_config.agent_id
            signed_url = await self._get_signed_url_for_agent(agent_id, config)
            if signed_url is None:
                raise Exception("Failed to get signed url for agent")
            self._ws = await websockets.connect(signed_url)
            logger.info({"message": "Connected to Ultravox voice engine"})
        except Exception as e:
            logger.error({"message": "Failed to connect to Ultravox voice engine", "error": str(e)})
            raise e

    async def _get_signed_url_for_agent(self, agent_id: str, config: SessionConfig) -> str | None:
        try:
            url = f"api/agents/{agent_id}/calls"
            body: dict = {}

            if config.agent is not None:
                if config.agent.ultravox_config is not None:
                    if config.agent.ultravox_config.template_config is not None:
                        body["templateContext"] = config.agent.ultravox_config.template_config
                    else:
                        body["templateContext"] = {}
                    if config.agent.ultravox_config.metadata is not None:
                        body["metadata"] = config.agent.ultravox_config.metadata
                    else:
                        body["metadata"] = {}
                    if config.agent.ultravox_config.medium is not None:
                        body["medium"] = config.agent.ultravox_config.medium
                    else:
                        body["medium"] = {
                            "serverWebSocket": {
                                "inputSampleRate": 8000,
                                "outputSampleRate": 8000,
                                "clientBufferSizeMs": 30000
                            }
                        }
                    if config.agent.ultravox_config.recording_enabled is not None:
                        body["recordingEnabled"] = config.agent.ultravox_config.recording_enabled
                    else:
                        body["recordingEnabled"] = True
                    if config.agent.ultravox_config.first_speaker_settings is not None:
                        body["firstSpeakerSettings"] = config.agent.ultravox_config.first_speaker_settings
                    else:
                        body["firstSpeakerSettings"] = {
                            "agent": {
                                "text": "Hi! How can I help you?"
                            }
                        }
            headers: dict = {
                "Content-Type": "application/json",
                "X-API-KEY": f"{self.api_key}"
            }

            response = await self.http_client.post(url, json_data=body, headers=headers)
            if response.get("joinUrl"):
                logger.info({"message": "Got signed url for agent from Ultravox", "join_url": response.get("joinUrl")})
                return response["joinUrl"]
            logger.error({"message": "Failed to get signed url for agent from Ultravox", "response": response})
            return None
        except Exception as e:
            logger.error({"message": "Failed to get signed url for agent from Ultravox", "error": str(e)})
            raise e

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()

    async def send(self, message: UnifiedMessage) -> None:
        if message.type == MessageType.AUDIO_CHUNK and isinstance(message, AudioChunk):
            if self._ws:
                # Decode base64 PCM and send as raw binary frame
                pcm_bytes = base64.b64decode(message.audio)
                await self._ws.send(pcm_bytes)
            return
        payload = self._to_voice_engine(message)
        if payload and self._ws:
            await self._ws.send(json.dumps(payload))

    def _to_voice_engine(self, message: UnifiedMessage) -> dict | None:
        """Unified → Ultravox wire format."""
        try:
            type = message.type
            # print("Ultravox to VoiceEngine: Type => ", type)
            match type:
                case MessageType.AUDIO_CHUNK:
                    # Ultravox handles audio via WebRTC data channel, not JSON
                    # For WebSocket mode, send raw base64
                    return None  # handled out-of-band

                case MessageType.USER_TEXT:
                    if isinstance(message, UserText):
                        return {
                        "type": "user_text_message",
                        "text": message.text,
                        "urgency": message.urgency.value,
                    }
                case MessageType.TOOL_RESULT:
                    if isinstance(message, ToolResult):
                        return {
                            "type": "client_tool_result",
                            "invocationId": message.tool_call_id,
                            "result": message.result,
                            **({"errorType": "implementation-error"} if message.is_error else {}),
                        }
                case MessageType.CONTEXT_UPDATE:
                    if isinstance(message, ContextUpdate):
                        return {
                            "type": "user_text_message",
                            "text": message.text,
                            "urgency": "later",
                        }
                case MessageType.HANG_UP:
                    if isinstance(message, HangUp):
                        return {
                            "type": "hang_up",
                            "message": message.message or "",
                        }
                case MessageType.PING:
                    if isinstance(message, Ping):
                        return {"type": "ping", "timestamp": message.timestamp}

                case _:
                    return None

        except Exception as e:
            logger.error({"message": "Failed to send message to Ultravox", "error": str(e)})
            raise e

    async def receive(self) -> AsyncGenerator[UnifiedMessage, None]:
        async def _generate():
            try:
                if self._ws is None:
                    raise Exception("Not connected to Ultravox voice engine")
                async for raw in self._ws:
                    # Ultravox sends audio as raw binary frames, everything else is JSON text
                    if isinstance(raw, bytes):
                        mulaw = audioop.lin2ulaw(raw, 2)
                        yield AudioResponse(
                            audio=base64.b64encode(mulaw).decode(),
                            event_id=None,
                        )
                        continue

                    # Text frame → JSON message
                    data = json.loads(raw)
                    msg = self._from_voice_engine(data)
                    if msg:
                        yield msg
            except Exception as e:
                logger.error({"message": "Failed to receive message from Ultravox voice engine", "error": str(e)})
                raise e

        return _generate()

    def _from_voice_engine(self, data: dict) -> UnifiedMessage | None:
        """Ultravox wire format → Unified."""
        try:
            t = data.get("type")
            # print("Ultravox: Type => ", t)
            match t:
                case "call_started":
                    return SessionReady(
                        session_id=data["callId"],
                        voice_engine=VoiceEngine.ULTRAVOX,
                    ) 
                case "state":
                    state_map = {
                        "idle": AgentState.IDLE,
                        "listening": AgentState.LISTENING,
                        "thinking": AgentState.THINKING,
                        "speaking": AgentState.SPEAKING,
                    }
                    return StateUpdate(state=state_map.get(data["state"], AgentState.IDLE))
                case "transcript":
                    role = data.get("role")
                    text = data.get("text") or data.get("delta") or ""
                    is_final = data.get("final", False)

                    logger.info({"message": "Received message from Ultravox voice engine", "role": role, "text": text, "is_final": is_final})
                    return Transcript(
                        role=TranscriptRole(role),
                        text=text,
                        is_final=is_final,
                        ordinal=data.get("ordinal"),
                    )
                case "client_tool_invocation":
                    return ToolCall(
                        tool_call_id=data["invocationId"],
                        tool_name=data["toolName"],
                        parameters=data.get("parameters", {}),
                    )

                case "pong":
                    return Pong(timestamp=data["timestamp"])

                case "debug":
                    return None  # skip debug messages

                case _:
                    return None
        except Exception as e:
            logger.error({"message": "Failed to receive message from Ultravox", "error": str(e)})
            raise e
