from ..schemas.telnyx import TelnyxOutboundCallSchema
from ..services.telnyx_service import TelnyxService
from app.utils.logger import logger


class TelnyxHandler:
    def __init__(self):
        self._telnyx_service = TelnyxService()

    async def make_outbound_call(self, tenant_id: str, call: TelnyxOutboundCallSchema):
        try:
            response = await self._telnyx_service.make_outbound_call(tenant_id, call)
            return response
        except Exception as e:
            logger.error({"message": "Failed to make outbound call", "error": str(e)})
            raise e
