from fastapi import Body, Form, Path, APIRouter, Request, WebSocket, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
# from app.core.schemas.telnyx import TelnyxOutboundCallSchema
from app.utils.logger import logger
from app.utils.response_util import error_response, success_response
from ..telephony.vonage import VonageTelephony
# from ..handlers.telnyx_handler import TelnyxHandler
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
import json


router = APIRouter(
    tags=["Vonage"],
    responses={404: {"description": "Not found"}},
)


@router.post('/{tenant_id}/outbound')
async def vonage_outbound_call(tenant_id: str, to: str,
        from_: str,
        agent_id: str,):
    try:

        result = await VonageTelephony().make_outbound_call(to=to, from_=from_, agent_id=agent_id)
        return success_response(message="Success", data={"data": result})
    except Exception as e:
        logger.error({"message": str(e), "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/media-stream")
async def vonage_media_stream(websocket: WebSocket):
    await websocket.accept()
    print("=== Vonage Media Stream ===")

    # voice_engine_instance = None
    agent_id = None
    voice_engine = None

    try:
        while True:
            message = await websocket.receive()

            # Text frame → JSON control message
            if "text" in message:
                data = json.loads(message["text"])
                event = data.get("event")
                print("Vonage event:", event, data)

                if event == "websocket:connected":
                    # Custom params are at the top level of this event
                    agent_id = data.get("agent_id")
                    voice_engine = data.get("voice_engine", "elevenlabs")
                    content_type = data.get("content-type", "audio/l16;rate=16000")
                    print(f"Connected: agent={agent_id} engine={voice_engine}")

                    # Connect to voice engine here
                    # voice_engine_instance = ...
                    # await voice_engine_instance.connect(config)

                elif event == "websocket:cleared":
                    print("Buffer cleared")

                elif event == "websocket:notify":
                    print("Notify:", data.get("payload"))

            # Binary frame → raw PCM audio from caller
            elif "bytes" in message:
                pcm_bytes = message["bytes"]
                # Send to voice engine
                # if voice_engine_instance:
                #     await voice_engine_instance.send(AudioChunk(...))
                pass

            # Connection closed
            elif message.get("type") == "websocket.disconnect":
                print("Vonage disconnected")
                break

    except Exception as e:
        logger.error({"message": "Vonage WS error", "error": str(e)})
    finally:
        # if voice_engine_instance:
            # await voice_engine_instance.disconnect()
        print("=== Vonage Session Ended ===")