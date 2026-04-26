import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class Env:
    """
    A class that contains constants for environment variables used in the service.
    """
    # Samvadam
    PORT: int = int(os.getenv("PORT", 8000))
    ENV_TYPE: str = os.getenv("ENV_TYPE", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    DOCS_USERNAME: str = os.getenv("DOCS_USERNAME", "admin")
    DOCS_PASSWORD: str = os.getenv("DOCS_PASSWORD", "admin")
    SAMVADAM_PUBLIC_URL: str = os.getenv("SAMVADAM_PUBLIC_URL", "http://localhost:3000")

    # Elevenlabs

    ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY") or None

    # Twilio
    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID") or None
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN") or None

    # Ultravox
    ULTRAVOX_API_KEY: str | None = os.getenv("ULTRAVOX_API_KEY") or None
