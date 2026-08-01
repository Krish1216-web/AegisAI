import sys
from loguru import logger
from app.core.config import settings

def setup_logging():
    """
    Configure Loguru handlers.
    In production mode, prints structured JSON logs for cloud aggregation.
    In development mode, prints colorized console logs.
    """
    # Clear default logger
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    if settings.ENVIRONMENT == "prod":
        # Production structured JSON logging
        logger.add(
            sys.stdout,
            serialize=True,
            level="INFO",
            backtrace=False,
            diagnose=False
        )
    else:
        # Development readable colorized logging
        logger.add(
            sys.stdout,
            format=log_format,
            level="DEBUG",
            colorize=True,
            backtrace=True,
            diagnose=True
        )

    logger.info(f"Logging initialized in [{settings.ENVIRONMENT}] mode.")
