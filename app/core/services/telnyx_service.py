from ..telephony.telnyx import TelnyxTelephony
from app.utils.logger import logger
from ..schemas.telnyx import TelnyxOutboundCallSchema


class TelnyxService:
    def __init__(self):
        self._telnyx_telephony = TelnyxTelephony()

    async def make_outbound_call(self, tenant_id: str, call: TelnyxOutboundCallSchema):
        try:
            response = await self._telnyx_telephony.make_outbound_call(call)
            return response
        except Exception as e:
            logger.error({"message": "Failed to make outbound call", "error": str(e)})
            raise e
