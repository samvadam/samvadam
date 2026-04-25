from ..schemas.unified import VoiceEngine


class VoiceEngineLibs:
    @staticmethod
    def voice_engine_audio_rate(provider: VoiceEngine) -> int:
        """Sample rate expected by each provider."""
        return {
            VoiceEngine.OPENAI: 16000,      # OpenAI wants 16kHz PCM
            VoiceEngine.ULTRAVOX: 8000,     # Ultravox accepts 8kHz
            VoiceEngine.ELEVENLABS: 8000,   # ElevenLabs accepts 8kHz
        }.get(provider, 8000)

    @staticmethod
    def get_voice_engine_for_twilio():
        return VoiceEngine.ELEVENLABS  # TODO : need to make dynamic
