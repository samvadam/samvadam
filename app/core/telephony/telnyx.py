from ..schemas.telnyx import TelnyxOutboundCallSchema
from telnyx import Client
from app.config.env import Env
from app.utils.logger import logger
from ..libs.samvadam import SamvadamLibs


class TelnyxTelephony:
    def __init__(self):
        api_key = Env.TELNYX_API_KEY
        if api_key is None:
            raise Exception("TELNYX_API_KEY is not set")
        self._api_key = api_key
        self._client = Client(api_key=api_key)

    async def make_outbound_call(self, call: TelnyxOutboundCallSchema):
        try:
            _from = call.from_
            to = call.to
            wss_url = SamvadamLibs.get_telnyx_media_stream_url()
            response = self._client.calls.dial(connection_id="2946536323130852811", from_=_from, to=to, stream_track="both_tracks", stream_url=wss_url)
            return response 
        except Exception as e:
            logger.error({"message": "Failed to make outbound call", "error": str(e)})
            raise e
