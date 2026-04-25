from ..services.twilio_service import TwilioService
from ..schemas.twilio import TOutboundCallRequestSchema, TwilioCallStatusWebhook
from typing import Dict, Any
from app.utils.logger import logger
from fastapi import WebSocket, Response
from app.config.env import Env


class TwilioHandler:
    def __init__(self):
        self.service = TwilioService()

    async def make_outbound_call(self, db_name: str, call: TOutboundCallRequestSchema) -> Dict[str, Any]:
        try:
            return await self.service.make_outbound_call(db_name, call)
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def handle_media_stream_handler(self, websocket: WebSocket):
        try:
            return await self.service.handle_media_stream_service(websocket)
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def handle_webhook(self, body: Dict[str, Any]) -> Response:
        try:
            return await self.service.handle_webhook(body)
        except Exception as e:
            logger.error({"message": str(e), "error": str(e)})
            raise e

    async def twilio_status_callback(self, call: TwilioCallStatusWebhook):
        try:
            return await self.service.twilio_status_callback_service(call)
        except Exception as e:
            logger.error({"message": "Failed While handling twilio status callback", "error": str(e)})
            raise e
