"""
ElevenLabs Conversational AI provider adapter.
Translates between unified schema ↔ ElevenLabs wire protocol.
"""
import json
from typing import AsyncGenerator
from app.config.env import Env
from app.utils.http.client import Client
from app.utils.logger import logger
import websockets
from app.audio.twilio import pcm16k_to_mulaw8k
from typing import Optional
from ..voice_engine.base import BaseVoiceEngine
from ..schemas.unified import (AgentResponse, AudioResponse, AudioChunk, ContextUpdate, Pong, SessionConfig, SessionReady, Transcript, TranscriptRole, ToolCall, ToolResult, UnifiedMessage, UserText, VoiceEngine, MessageType)


class ElevenLabsVoiceEngine(BaseVoiceEngine):
    @property
    def name(self) -> str:
        return "elevenlabs"

    def __init__(self):
        self.api_key = Env.ELEVENLABS_API_KEY
        if self.api_key is None:
            raise Exception("ELEVENLABS_API_KEY is not set")
        self.client = Client("https://api.elevenlabs.io")
        self._ws: websockets.ClientConnection | None = None

    async def connect(self, config: SessionConfig) -> None:
        try:
            if config.agent is None:
                raise Exception("Agent Config is not set")
            agent_config = config.agent

            if agent_config.agent_id is None:
                raise Exception("Agent ID is not set")
            agent_id = agent_config.agent_id

            signed_url = await self._get_signed_url_for_agent(agent_id)
            if signed_url is None:
                raise Exception("Failed to get signed url for agent")

            self._ws = await websockets.connect(signed_url)
            logger.info({"message": "Connected to  ElevenLabs voice engine"})
            # Build initiation payload
            override: dict = {}
            if config.agent:
                agent_block: dict = {}
                if config.agent.prompt:
                    agent_block["prompt"] = {"prompt": config.agent.prompt}
                if config.agent.first_message:
                    agent_block["first_message"] = config.agent.first_message
                if config.agent.language:
                    agent_block["language"] = config.agent.language
                if agent_block:
                    override["agent"] = agent_block
                if config.agent.voice_id:
                    override["tts"] = {"voice_id": config.agent.voice_id}

            payload: dict = {"type": "conversation_initiation_client_data"}
            if override:
                payload["conversation_config_override"] = override
            if config.dynamic_vars:
                payload["dynamic_variables"] = config.dynamic_vars
            if config.extra:
                payload["custom_llm_extra_body"] = config.extra
            await self._ws.send(json.dumps(payload))
        except Exception as e:
            logger.error({"message": "Failed to connect to voice engine", "error": str(e)})
            raise e

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()

    async def send(self, message: UnifiedMessage) -> None:
        payload = self._to_voice_engine(message)
        if payload and self._ws:
            await self._ws.send(json.dumps(payload))

    def _to_voice_engine(self, message: UnifiedMessage) -> dict | None:
        """Unified → ElevenLabs wire format."""
        try:
            match message.type:
                case MessageType.AUDIO_CHUNK:
                    if isinstance(message, AudioChunk):
                        return {"user_audio_chunk": message.audio}

                case MessageType.USER_TEXT:
                    if isinstance(message, UserText):
                        return {"type": "user_message", "text": message.text}

                case MessageType.TOOL_RESULT:
                    if isinstance(message, ToolResult):
                        return {"type": "client_tool_result", "tool_name": message.tool_name, "tool_call_id": message.tool_call_id, "result": message.result, "is_error": message.is_error}

                case MessageType.CONTEXT_UPDATE:
                    if isinstance(message, ContextUpdate):
                        return {"type": "contextual_update", "text": message.text}

                case MessageType.HANG_UP:
                    # ElevenLabs has no explicit hang_up; close the socket
                    return None  # handled via disconnect()

                case MessageType.PING:
                    # ElevenLabs server sends ping; client just responds with pong
                    return None

                case _:
                    return None

        except Exception as e:
            logger.error({"message": "Failed to send message to ElevenLabs voice engine", "error": str(e)})
            raise e

    async def receive(self) -> AsyncGenerator[UnifiedMessage, None]:
        async def _generate():
            try:
                if self._ws is None:
                    raise Exception("Not connected to ElevenLabs voice engine")
                async for raw in self._ws:
                    data = json.loads(raw)
                    msg = self._from_voice_engine(data)
                    if msg:
                        yield msg
            except Exception as e:
                logger.error({"message": "Failed to receive message from ElevenLabs voice engine", "error": str(e)})
                raise e

        return _generate()

    def _from_voice_engine(self, data: dict) -> UnifiedMessage | None:
        try:
            """ElevenLabs wire format → Unified."""
            t = data.get("type")
            # logger.info({"message": "Received message from ElevenLabs voice engine", "type": t})
            match t:
                case "conversation_initiation_metadata":
                    meta = data.get("conversation_initiation_metadata_event", {})
                    return SessionReady(
                        session_id=meta.get("conversation_id", ""),
                        voice_engine=VoiceEngine.ELEVENLABS,
                        audio_format=meta.get("agent_output_audio_format"),
                    )
                case "user_transcript":
                    event = data.get("user_transcription_event", {})
                    text = event.get("user_transcript", "")
                    logger.info({"message": "User transcript", "text": text, "role": TranscriptRole.USER})
                    return Transcript(
                        role=TranscriptRole.USER,
                        text=text,
                        is_final=True,
                    )

                case "agent_response":
                    event = data.get("agent_response_event", {})
                    text = event.get("agent_response", "")
                    logger.info({"message": "Agent response", "text": text, "role": TranscriptRole.AGENT})
                    return AgentResponse(
                        text=text,
                        is_final=True,
                    )

                case "internal_tentative_agent_response":
                    event = data.get("tentative_agent_response_internal_event", {})
                    return AgentResponse(
                        text=event.get("tentative_agent_response", ""),
                        is_final=False,
                    )

                case "audio":
                    event = data.get("audio_event", {})
                    chunk: Optional[str] = (
                                    data.get("audio_event", {}).get("audio_base_64") or data.get("audio", {}).get("chunk")
                                ) or ""
                    mulaw_chunk = pcm16k_to_mulaw8k(chunk)
                    return AudioResponse(
                        audio=mulaw_chunk,
                        event_id=event.get("event_id"),
                    )

                case "client_tool_call":
                    call = data.get("client_tool_call", {})
                    return ToolCall(
                        tool_call_id=call.get("tool_call_id", ""),
                        tool_name=call.get("tool_name", ""),
                        parameters=call.get("parameters", {}),
                    )

                case "ping":
                    # Auto-respond with pong
                    event = data.get("ping_event", {})
                    event_id = event.get("event_id", 0)
                    # Send pong back to ElevenLabs immediately
                    if self._ws:
                        import asyncio
                        asyncio.create_task(
                            self._ws.send(json.dumps({"type": "pong", "event_id": event_id}))
                        )
                    return None

                case "vad_score":
                    return None  # internal, not surfaced in unified schema

                case _:
                    return None
            return None
        except Exception as e:
            logger.error({"message": "Failed to receive message from ElevenLabs voice engine", "error": str(e)})
            raise e

    async def _get_signed_url_for_agent(self, agent_id: str) -> str | None:
        try:
            url = f"/v1/convai/conversation/get-signed-url?agent_id={agent_id}"

            headers = {
                "Content-Type": "application/json",
                "XI-API-KEY": f"{self.api_key}"
            }

            response = await self.client.get(url, headers=headers)

            if response.get("signed_url"):
                return response["signed_url"]
            logger.error({"message": "Failed to get signed url for agent", "response": response})
            return None
        except Exception as e:
            logger.error({"message": "Failed to get signed url for agent", "error": str(e)})
            raise e
