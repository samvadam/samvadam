from app.utils.logger import logger
import os


def load_all_env():
    required_vars = [
        # Application
        "PORT",
        "ENV_TYPE",
        "LOG_LEVEL",
        "DOCS_USERNAME",
        "DOCS_PASSWORD",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")

    logger.info("All required environment variables are set.")
