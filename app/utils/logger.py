import logging
import os
import json
from datetime import datetime

# Set logs directory at root
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))
os.makedirs(LOG_DIR, exist_ok=True)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName,
            "message": record.getMessage()
        }
        return json.dumps(log_record)


# Create logger only once
logger = logging.getLogger("app-logger")
logger.setLevel(logging.INFO)

# Avoid adding handlers multiple times if already configured
if not logger.handlers:
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"))
    file_handler.setFormatter(JsonFormatter())

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def x_logger_response(x_request_id: str, message: str, **kwargs):
    return {
        "x-request-id": x_request_id,
        "message": message,
        **kwargs
    }
