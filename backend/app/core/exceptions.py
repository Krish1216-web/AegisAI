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
        if exc.code == "ENTITY_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code == "DATABASE_TRANSACTION_FAILED" or exc.code == "MCP_SERVER_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

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
