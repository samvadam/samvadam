
from ..voice_engine.base import BaseVoiceEngine
from app.config.env import Env
from app.utils.logger import logger
from fastapi import WebSocket, WebSocketDisconnect
import json
import base64
import audioop
from ..voice_engine.libs import VoiceEngineLibs
from typing import Optional
from ..schemas.unified import SessionConfig, AgentConfig, MessageType, AudioChunk, AudioResponse, SessionReady, VoiceEngine, ElevenlabsConfig, UltravoxConfig
from ..voice_engine.elevenlabs import ElevenLabsVoiceEngine
from ..voice_engine.ultravox import UltravoxVoiceEngine
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException, TwilioServiceException
from ..schemas.twilio import TwilioCallSchema
from ..libs.samvadam import SamvadamLibs
from twilio.rest.api.v2010.account.call import CallInstance
import asyncio


class TwilioTelephony:
    def __init__(self):
        self._account_sid = Env.TWILIO_ACCOUNT_SID
        if self._account_sid is None:
            raise Exception("TWILIO_ACCOUNT_SID is not set")
        self._auth_token = Env.TWILIO_AUTH_TOKEN
        if self._auth_token is None:
            raise Exception("TWILIO_AUTH_TOKEN is not set")

        username = Env.TWILIO_ACCOUNT_SID
        password = Env.TWILIO_AUTH_TOKEN
        account_sid = Env.TWILIO_ACCOUNT_SID
        self.client = Client(username=username, password=password, account_sid=account_sid)

    async def make_outbound_call(self, call: TwilioCallSchema) -> CallInstance:
        try:

            # Convert model to dict, using the alias 'from' for the 'from_' field
            # and excluding None values so we don't override Twilio defaults
            url = SamvadamLibs.get_twilio_webhook_url()
            call.url = url
            call_data = call.model_dump(exclude_none=True, exclude_unset=True)

            # ** to unpack the dictionary into keyword arguments
            result = self.client.calls.create(**call_data)
            return result
        except TwilioRestException as e:
            logger.error({"message": e.msg, "code": e.code, "error": str(e)})
            raise e
        except TwilioServiceException as e:
            logger.error({"message": e.detail, "code": e.code, "error": str(e)})
            raise e
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def twilio_media_stream(self, twilio_ws: WebSocket):
        """
        Twilio Media Stream WebSocket handler.

        Twilio message types we handle:
        connected   → stream is ready
        start       → call metadata (stream SID, call SID, custom params)
        media       → audio chunk from caller (base64 mulaw 8kHz)
        stop        → call ended

        We send back:
        media       → audio for Twilio to play to the caller
        mark        → synchronization marker
        clear       → drop buffered audio (for interruptions)
        """
        try:
            await twilio_ws.accept()
            logger.info({"message": "Twilio WebSocket connected"})

            voice_engine_instance: Optional[BaseVoiceEngine] = None
            stream_sid: Optional[str] = None
            # target_provider = VoiceEngineLibs.get_voice_engine_for_twilio()
            # audio_rate = VoiceEngineLibs.voice_engine_audio_rate(target_provider)
            ratecv_state_holder: list[Optional[tuple]] = [None]
            voice_engine_audio_format: Optional[str] = None

            # Custom Parameter from twilio
            voice_engine: Optional[str] = None
            agent_id: Optional[str] = None

            async def _send_audio_to_twilio(mulaw_chunk: str):
                """Send PCM16 audio from voice engine back to Twilio as mulaw."""

                await twilio_ws.send_text(json.dumps({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": mulaw_chunk},
                }))

            async def voice_engine_to_twilio():
                """Read audio from provider, send to Twilio."""
                try:
                    if voice_engine_instance is None:
                        raise Exception("Voice engine instance is not set")

                    async for msg in await voice_engine_instance.receive():
                        nonlocal voice_engine_audio_format

                        # type = msg.type
                        # print("type", type)

                        if msg.type == MessageType.SESSION_READY:
                            if isinstance(msg, SessionReady):
                                voice_engine_audio_format = msg.audio_format

                        if msg.type == MessageType.AUDIO_RESPONSE:
                            if isinstance(msg, AudioResponse): 
                                await _send_audio_to_twilio(msg.audio)

                except WebSocketDisconnect:
                    logger.info({"message": "Twilio WebSocket disconnected"})
                except Exception as e:
                    logger.error({"message": "Twilio WebSocket error", "error": str(e)})

            try:
                async for raw in twilio_ws.iter_text():
                    data = json.loads(raw)
                    event = data.get("event")

                    match event:
                        case "connected":
                            logger.info({"message": "Twilio Stream connected"})

                        case "start":
                            stream_sid = data.get("streamSid")
                            start = data.get("start", {})
                            call_sid = start.get("callSid", "")
                            custom_params = start.get("customParameters", {})
                            logger.info({"message": "Twilio Stream started", "call_sid": call_sid, "custom_params": custom_params})

                            agent_id = custom_params.get("agent_id")
                            voice_engine = custom_params.get("voice_engine")

                            if agent_id is None:
                                logger.error({"message": "Agent ID is not set"})
                                raise Exception("Agent ID is not set")
                            if voice_engine is None:
                                logger.error({"message": "Voice engine is not set"})
                                raise Exception("Voice engine is not set")

                            voice_engine_instance = await self._get_voice_engine_instance(voice_engine, agent_id)

                            if voice_engine_instance is None:
                                logger.error({"message": "Voice engine instance is not set"})
                                raise Exception("Voice engine instance is not set")

                            config = await self._get_voice_engine_config(voice_engine, agent_id, custom_params)
                            if config is None:
                                logger.error({"message": "Failed to get voice engine config"})
                                raise Exception("Failed to get voice engine config")

                            await voice_engine_instance.connect(config)
                            logger.info({"message": "Voice engine connected"})

                            # Start listening to voice engine in background
                            asyncio.create_task(voice_engine_to_twilio())

                        case "media":
                            if not voice_engine_instance:
                                continue

                            # ElevenLabs
                            if voice_engine == VoiceEngine.ELEVENLABS:
                                mulaw_b64 = data["media"]["payload"]
                                mulaw_bytes = base64.b64decode(mulaw_b64)

                                # mulaw -> linear PCM (8kHz, 16-bit)
                                pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)

                                # 8kHz -> 16kHz with stateful resampling to avoid clicks/pops
                                pcm_16k, ratecv_state_holder[0] = audioop.ratecv(
                                    pcm_8k, 2, 1, 8000, 16000, ratecv_state_holder[0]
                                )
                                pcm_b64 = base64.b64encode(pcm_16k).decode("utf-8")
                                await voice_engine_instance.send(AudioChunk(audio=pcm_b64))

                            elif voice_engine == VoiceEngine.ULTRAVOX:
                                mulaw_b64 = data["media"]["payload"]
                                mulaw_bytes = base64.b64decode(mulaw_b64)

                                # mulaw → linear PCM 16-bit at 8kHz
                                pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
                                pcm_b64 = base64.b64encode(pcm_8k).decode("utf-8")

                                await voice_engine_instance.send(AudioChunk(audio=pcm_b64))

                        case "stop":
                            logger.info({"message": "Twilio Stream stopped"})
                            break

                        case _:
                            logger.debug({"message": "Twilio Stream received unknown event", "event": event})
            except WebSocketDisconnect:
                logger.info({"message": "Twilio WebSocket disconnected"})
            except Exception as e:
                logger.error({"message": "Twilio WebSocket error", "error": str(e)})
            finally:
                ratecv_state_holder[0] = None
                if voice_engine_instance:
                    await voice_engine_instance.disconnect()
                logger.info({"message": "Twilio WebSocket Ended"})
        except Exception as e:
            logger.error({"message": "Twilio WebSocket error", "error": str(e)})
            raise e

    async def _get_voice_engine_instance(self, voice_engine: str, agent_id: str) -> BaseVoiceEngine | None:
        try:
            if voice_engine == VoiceEngine.ELEVENLABS:
                return ElevenLabsVoiceEngine()
            elif voice_engine == VoiceEngine.ULTRAVOX:
                return UltravoxVoiceEngine()
            # elif voice_engine == VoiceEngine.OPENAI:
            #     return 
            #     return ElevenLabsVoiceEngine()
            else:
                raise Exception("Unknown voice engine")
        except Exception as e:
            logger.error({"message": "Failed to get voice engine instance", "error": str(e)})
            raise e

    async def _get_voice_engine_config(self, voice_engine: str, agent_id: str, extra: dict) -> SessionConfig | None:
        try:
            if voice_engine == VoiceEngine.ELEVENLABS:
                config = SessionConfig(
                    agent=AgentConfig(
                        agent_id=agent_id,
                        elevenlabs_config=ElevenlabsConfig()
                    ),
                    extra=extra
                )
                return config
            elif voice_engine == VoiceEngine.ULTRAVOX:
                config = SessionConfig(
                    agent=AgentConfig(
                        agent_id=agent_id,
                        ultravox_config=UltravoxConfig(
                            medium={
                                "serverWebSocket": {
                                "inputSampleRate": 8000,
                                "outputSampleRate": 8000,
                                "clientBufferSizeMs": 30000
                            }
                            },
                            first_speaker_settings={
                                "agent": {
                                    "text": "Hi! This is Raj from Even HealthCare. How's your day going?"
                                }
                            },
                            recording_enabled=True,
                            metadata={},
                            template_config={}
                        )
                    )
                )
                return config
            elif voice_engine == VoiceEngine.OPENAI:
                pass
            else:
                raise Exception("Unknown voice engine")
        except Exception as e:
            logger.error({"message": "Failed to get voice engine config", "error": str(e)})
            raise e
