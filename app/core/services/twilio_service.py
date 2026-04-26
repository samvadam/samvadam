
from ..telephony.twilio import TwilioTelephony
from ..schemas.twilio import TOutboundCallRequestSchema, TwilioCallWebhook, TwilioCallStatusWebhook
from typing import Dict, Any, Optional
from twilio.rest.api.v2010.account.call import CallInstance
from fastapi import WebSocket, Response
from app.utils.logger import logger
from app.config.env import Env
from ..libs.samvadam import SamvadamLibs
from ..schemas.unified import VoiceEngine
import asyncio


class TwilioService:
    def __init__(self):
        self.client = TwilioTelephony()

    async def make_outbound_call(self, db_name: str, call: TOutboundCallRequestSchema) -> Dict[str, Any]:
        try:
            call_instance = await self.client.make_outbound_call(call=call)
            return self._call_instance_to_dict(instance=call_instance)
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def handle_media_stream_service(self, websocket: WebSocket):
        try:
            await self.client.twilio_media_stream(websocket)
        except Exception as e:
            logger.error({"message": "Failed While handling media stream", "error": str(e)})

    async def handle_webhook(self, body: Dict[str, Any]) -> Response:
        try:
            print("=== TWILIO Webhook Call ===")

            trunk_url = SamvadamLibs.get_public_url().replace("https://", "").replace("http://", "")
            ws_url = f"wss://{trunk_url}/api/v1/twilio/media-stream"
            print("ws_url", ws_url)
            # voice_engine = VoiceEngine.ULTRAVOX.value
            # agent_id = "6df9bf14-86db-4b4f-a88d-937b45d153c1"
            voice_engine = VoiceEngine.ELEVENLABS.value
            agent_id = "agent_5701kjdhahcgf3wr1g7q7p7v4608"
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Connect>
                        <Stream url="{ws_url}">
                            <Parameter name="voice_engine" value="{voice_engine}" />
                            <Parameter name="agent_id" value="{agent_id}" />
                        </Stream>
                    </Connect>
                </Response>"""

            print("twiml: ", twiml)
            return Response(content=twiml, media_type="text/xml")
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def twilio_status_callback_service(self, call: TwilioCallStatusWebhook):
        try:
            await asyncio.sleep(30)  # Wait for 30 seconds for elevenlabs to process

            logger.info({"message": "Twilio Status Callback", "call_sid": call.call_sid, "call": call.model_dump()})

        except Exception as e:
            logger.error({"message": "Failed While handling twilio status callback", "error": str(e)})
            raise e

    def _call_instance_to_dict(self, instance: CallInstance) -> Dict[str, Any]:
        return {
            "sid": instance.sid,
            "account_sid": instance.account_sid,
            "to": instance.to,
            "to_formatted": instance.to_formatted,
            "from": instance._from,  # Accessing the internal _from attribute
            "from_formatted": instance.from_formatted,
            "status": str(instance.status) if instance.status else None,
            "price_unit": instance.price_unit,
            "direction": instance.direction,
        }
