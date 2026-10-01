import sys
import os
import json
import datetime
from loguru import logger
from typing import Any, Dict

from app.core.config import settings
from app.core.mcp.security import CredentialStore
from app.core.correlation import get_correlation_context


def structured_json_sink(message) -> None:
    """
    Loguru custom sink that serializes log records into canonical JSON format
    enriched with correlation context and scrubbed of any secret credentials.
    """
    record = message.record
    corr_ctx = get_correlation_context()

    # Redact message string
    raw_message = record["message"]
    clean_message = CredentialStore.redact_sensitive_str(raw_message)

    # Redact extra metadata
    clean_extra = CredentialStore.redact_sensitive_dict(dict(record.get("extra", {})))

    log_entry: Dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "component": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": clean_message,
        "request_id": corr_ctx.get("request_id"),
        "correlation_id": corr_ctx.get("correlation_id"),
        "execution_id": corr_ctx.get("execution_id"),
        "job_id": corr_ctx.get("job_id"),
        "workflow_id": corr_ctx.get("workflow_id"),
        "workspace_id": corr_ctx.get("workspace_id"),
        "user_id": corr_ctx.get("user_id"),
        "extra": clean_extra
    }

    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else "Exception",
            "value": CredentialStore.redact_sensitive_str(str(record["exception"].value))
        }

    sys.stdout.write(json.dumps(log_entry) + "\n")
    sys.stdout.flush()


def setup_logging():
    """
    Configure Loguru logging handlers for production and development.
    Production uses structured JSON logging with correlation propagation and secret scrubbing.
    Development uses readable colorized text format.
    """
    logger.remove()

    configured_level = getattr(settings, "LOG_LEVEL", "INFO").upper()

    if settings.ENVIRONMENT == "prod":
        # Production JSON stdout sink
        logger.add(
            structured_json_sink,
            level=configured_level,
            backtrace=False,
            diagnose=False
        )

        # Production rotating file log if path configured
        log_file_path = getattr(settings, "LOG_FILE_PATH", None)
        if log_file_path:
            try:
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                logger.add(
                    log_file_path,
                    rotation=getattr(settings, "LOG_ROTATION", "100 MB"),
                    retention=getattr(settings, "LOG_RETENTION", "10 days"),
                    compression="zip",
                    level=configured_level,
                    serialize=True,
                    backtrace=False,
                    diagnose=False
                )
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to configure file logging at '{log_file_path}': {e}\n")
    else:
        # Development readable console logging
        dev_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            format=dev_format,
            level=configured_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )

    logger.info(f"Structured logging initialized in [{settings.ENVIRONMENT}] mode (level={configured_level}).")
