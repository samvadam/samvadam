import time
import uuid
import os
import httpx
from authlib.jose import jwt
from app.config.env import Env
from app.utils.logger import logger
from ..libs.samvadam import SamvadamLibs


class VonageTelephony:
    def __init__(self):
        self._application_id = Env.VONAGE_APPLICATION_ID
        if self._application_id is None:
            raise Exception("VONAGE_APPLICATION_ID is not set")

        key_path = Env.VONAGE_PRIVATE_KEY_FILE_APTH
        if key_path is None:
            raise Exception("VONAGE_PRIVATE_KEY_FILE_PATH is not set")
        if os.path.isfile(key_path):
            self._private_key = open(key_path).read()
        else:
            raise Exception("VONAGE_PRIVATE_KEY_FILE_PATH is not set")
        if self._private_key is None:
            raise Exception("VONAGE_PRIVATE_KEY is not set")

    def _generate_jwt(self) -> str:
        payload = {
            "application_id": self._application_id,
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(
            {"alg": "RS256"},
            payload,
            self._private_key,
        )
        return token.decode() if isinstance(token, bytes) else token

    async def make_outbound_call(
        self,
        to: str,
        from_: str,
        agent_id: str,
        voice_engine: str = "elevenlabs",
    ):
        try:
            ws_url = SamvadamLibs.get_vonage_media_stream_url().replace("https://", "wss://").replace("http://", "ws://")
            print("ws_url", ws_url)

            token = self._generate_jwt()

            body = {
                "to": [{"type": "phone", "number": to}],
                "from": {"type": "phone", "number": from_},
                "ncco": [
                    {
                        "action": "connect",
                        "endpoint": [
                            {
                                "type": "websocket",
                                "uri": ws_url,
                                "content-type": "audio/l16;rate=16000",
                                "headers": {
                                    "agent_id": agent_id,
                                    "voice_engine": voice_engine,
                                },
                            }
                        ],
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.nexmo.com/v1/calls",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=30,
                )

            data = response.json()

            if response.status_code != 201:
                raise Exception(f"Vonage API error: {data}")

            logger.info({"message": "Outbound call created", "call_uuid": data.get("uuid")})
            return data

        except Exception as e:
            logger.error({"message": "Failed to make outbound call", "error": str(e)})
            raise e
