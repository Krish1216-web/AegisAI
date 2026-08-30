from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Dict, Any

class AegisBaseException(Exception):
    """
    Base domain exception class for AegisAI application.
    """
    def __init__(self, message: str, code: str = "INTERNAL_SERVER_ERROR", details: Any = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

class EntityNotFoundError(AegisBaseException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, code="ENTITY_NOT_FOUND", details=details)

class DatabaseError(AegisBaseException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, code="DATABASE_TRANSACTION_FAILED", details=details)

class McpConnectionError(AegisBaseException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, code="MCP_SERVER_UNAVAILABLE", details=details)

# FastAPI custom handlers registration mapping
def register_exception_handlers(app):
    @app.exception_handler(AegisBaseException)
    async def aegis_exception_handler(request: Request, exc: AegisBaseException):
        logger.error(f"Domain Exception [{exc.code}]: {exc.message} - Details: {exc.details}")
        
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if exc.code == "ENTITY_NOT_FOUND" or exc.code == "DOCUMENT_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code in ["UNSUPPORTED_FILE_TYPE", "DOCUMENT_TOO_LARGE", "INVALID_FILE"]:
            status_code = status.HTTP_400_BAD_REQUEST
        elif exc.code == "PERMISSION_DENIED":
            status_code = status.HTTP_403_FORBIDDEN
        elif exc.code == "DUPLICATE_DOCUMENT":
            status_code = status.HTTP_409_CONFLICT
        elif exc.code in ["DATABASE_TRANSACTION_FAILED", "MCP_SERVER_UNAVAILABLE"]:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code == "STORAGE_ERROR":
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.opt(exception=exc).error("Unhandled system exception encountered.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "UNEXPECTED_SYSTEM_ERROR",
                    "message": "An unhandled error occurred inside the gateway routing logic.",
                    "details": str(exc)
                }
            }
        )
