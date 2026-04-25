from fastapi import Body, Form, Path, APIRouter, Request, WebSocket, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.core.schemas.twilio import TwilioCallStatusWebhook, TOutboundCallRequestSchema
from app.utils.logger import logger
from app.utils.response_util import error_response, success_response
from ..handlers.twilio_handler import TwilioHandler
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

router = APIRouter(
    tags=["Twilio"],
    responses={404: {"description": "Not found"}},
)


@router.post('/{tenant_id}/outbound')
async def twilio_outbound_call(tenant_id: str, call: TOutboundCallRequestSchema = Body(...)):
    try:

        result = await TwilioHandler().make_outbound_call(tenant_id, call)
        return success_response(message="Success", data={"data": result})
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def twilio_webhook(request: Request):
    try:
        form_data = await request.form()
        # Convert to a dict so handler works as expected
        body = dict(form_data)

        handler = TwilioHandler()
        return await handler.handle_webhook(body)
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/media-stream")
async def twilio_media_stream(websocket: WebSocket):
    try:
        handler = TwilioHandler()
        await handler.handle_media_stream_handler(websocket)
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status-callback")
async def twilio_status_callback(background_tasks: BackgroundTasks, call: TwilioCallStatusWebhook = Form(...)):
    try:
        print("Status Body: ", call)
        handler = TwilioHandler()
        background_tasks.add_task(handler.twilio_status_callback, call)
        return {"status": "success"}
    except Exception as e:
        logger.error({"message": str(e)})
        raise HTTPException(status_code=500, detail="Internal Server Error")
