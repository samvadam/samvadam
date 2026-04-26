from fastapi import Body, Form, Path, APIRouter, Request, WebSocket, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.core.schemas.telnyx import TelnyxOutboundCallSchema
from app.utils.logger import logger
from app.utils.response_util import error_response, success_response
from ..handlers.telnyx_handler import TelnyxHandler
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

router = APIRouter(
    tags=["Telnyx"],
    responses={404: {"description": "Not found"}},
)


@router.post('/{tenant_id}/outbound')
async def telnyx_outbound_call(tenant_id: str, call: TelnyxOutboundCallSchema = Body(...)):
    try:

        result = await TelnyxHandler().make_outbound_call(tenant_id, call)
        return success_response(message="Success", data={"data": result})
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/media-stream")
async def telnyx_media_stream(websocket: WebSocket):
    try:
        print("=== Telnyx Media Stream ===")
        await websocket.accept()

        async for raw in websocket.iter_text():
            print(raw)
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
