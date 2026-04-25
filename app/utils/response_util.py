from fastapi.responses import JSONResponse
from typing import Dict, Any


def success_response(data: Dict[Any, Any], message: str = "Success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(content={"success": True, "message": message, "data": data}, status_code=status_code)


def error_response(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(content={"success": False, "message": message}, status_code=status_code)
