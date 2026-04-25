"""
Audio conversion utilities for Twilio Media Streams.

Twilio sends/receives audio as:
  - Encoding: mulaw (G.711 u-law)
  - Sample rate: 8000 Hz
  - Channels: mono

Most voice Voice Engines expect:
  - Encoding: PCM 16-bit linear
  - Sample rate: 8000–16000 Hz
  - Channels: mono

This module handles the conversion in both directions.
"""
import audioop
import base64


# ─────────────────────────────────────────
# Twilio → Voice Engine
# ─────────────────────────────────────────

# def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
#     """Convert 8kHz mulaw bytes to 16-bit PCM bytes."""
#     return audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit width


# def mulaw_to_pcm16_base64(mulaw_b64: str) -> str:
#     """
#     Decode base64 mulaw, convert to PCM16, return as base64.
#     Use this when forwarding Twilio audio to a Voice Engine.
#     """
#     mulaw_bytes = base64.b64decode(mulaw_b64)
#     pcm_bytes = mulaw_to_pcm16(mulaw_bytes)
#     return base64.b64encode(pcm_bytes).decode()


# def upsample_8k_to_16k(pcm8k_bytes: bytes) -> bytes:
#     """
#     Upsample PCM audio from 8kHz to 16kHz by simple 2x linear interpolation.
#     Required for Voice Engines that only accept 16kHz input (e.g. OpenAI Realtime).
#     """
#     return audioop.ratecv(pcm8k_bytes, 2, 1, 8000, 16000, None)[0]


# def mulaw_to_pcm16_16k_base64(mulaw_b64: str) -> str:
#     """
#     Full pipeline: base64 mulaw 8kHz → base64 PCM16 16kHz.
#     Use for Voice Engines requiring 16kHz (OpenAI Realtime).
#     """
#     mulaw_bytes = base64.b64decode(mulaw_b64)
#     pcm8k = mulaw_to_pcm16(mulaw_bytes)
#     pcm16k = upsample_8k_to_16k(pcm8k)
#     return base64.b64encode(pcm16k).decode()


# # ─────────────────────────────────────────
# # Voice Engine → Twilio
# # ─────────────────────────────────────────

# def pcm16_to_mulaw(pcm_bytes: bytes) -> bytes:
#     """Convert 16-bit PCM bytes to 8kHz mulaw bytes."""
#     return audioop.lin2ulaw(pcm_bytes, 2)


# def downsample_16k_to_8k(pcm16k_bytes: bytes) -> bytes:
#     """Downsample PCM from 16kHz to 8kHz."""
#     return audioop.ratecv(pcm16k_bytes, 2, 1, 16000, 8000, None)[0]


# def pcm16_to_mulaw_base64(pcm_b64: str, source_rate: int = 8000) -> str:
#     """
#     Convert Voice Engine audio (PCM16, any rate) back to base64 mulaw 8kHz for Twilio.
#     source_rate: sample rate of the incoming PCM audio.
#     """
#     pcm_bytes = base64.b64decode(pcm_b64)
#     if source_rate != 8000:
#         pcm_bytes = audioop.ratecv(pcm_bytes, 2, 1, source_rate, 8000, None)[0]
#     mulaw = pcm16_to_mulaw(pcm_bytes)
#     return base64.b64encode(mulaw).decode()


def mulaw_to_pcm16k(mulaw_b64: str) -> str:
    """Convert Twilio mulaw/8kHz audio to PCM/16kHz base64 for ElevenLabs."""
    mulaw_bytes = base64.b64decode(mulaw_b64)
    # mulaw -> linear PCM 16-bit
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
    # 8kHz -> 16kHz (upsample by 2)
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return base64.b64encode(pcm_16k).decode("utf-8")


def pcm16k_to_mulaw8k(pcm_b64: str) -> str:
    """Convert ElevenLabs PCM/16kHz audio to mulaw/8kHz base64 for Twilio."""
    pcm_16k = base64.b64decode(pcm_b64)
    # 16kHz -> 8kHz (downsample)
    pcm_8k, _ = audioop.ratecv(pcm_16k, 2, 1, 16000, 8000, None)
    # linear PCM 16-bit -> mulaw
    mulaw_bytes = audioop.lin2ulaw(pcm_8k, 2)
    return base64.b64encode(mulaw_bytes).decode("utf-8")
