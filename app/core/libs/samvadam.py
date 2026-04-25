from app.config.env import Env


class SamvadamLibs:
    def __init__(self):
        pass

    @staticmethod
    def get_public_url() -> str:
        return Env.SAMVADAM_PUBLIC_URL

    @staticmethod
    def get_twilio_webhook_url() -> str:
        return f"{Env.SAMVADAM_PUBLIC_URL}/api/v1/twilio/webhook"
