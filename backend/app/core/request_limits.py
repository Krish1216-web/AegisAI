"""
Request body size limiter middleware for AegisAI.
Enforces size boundaries across JSON APIs and streaming multipart uploads to protect against DoS.
"""
import json
from starlette.types import ASGIApp, Scope, Receive, Send
from app.core.config import settings

class RequestSizeLimitMiddleware:
    """
    Pure ASGI middleware that bounds payload sizes based on route characteristics.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Differentiate limits: File uploads get MAX_UPLOAD_BYTES, general endpoints get MAX_REQUEST_BODY_BYTES
        if "/documents/upload" in path:
            max_bytes = getattr(settings, "MAX_UPLOAD_BYTES", 50 * 1024 * 1024)
        else:
            max_bytes = getattr(settings, "MAX_REQUEST_BODY_BYTES", 10 * 1024 * 1024)

        # 1. Check Content-Length header if present
        headers = dict(scope.get("headers", []))
        content_length_hdr = headers.get(b"content-length")
        if content_length_hdr:
            try:
                cl_val = int(content_length_hdr.decode("latin1"))
                if cl_val > max_bytes:
                    await self._send_413(send, max_bytes)
                    return
            except ValueError:
                pass

        # 2. Check streaming body size
        bytes_received = 0
        async def wrapped_receive():
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > max_bytes:
                    raise ValueError("PayloadTooLarge")
            return message

        try:
            await self.app(scope, wrapped_receive, send)
        except ValueError as e:
            if str(e) == "PayloadTooLarge":
                await self._send_413(send, max_bytes)
            else:
                raise

    async def _send_413(self, send: Send, max_bytes: int):
        body = json.dumps({
            "success": False,
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": f"Request body exceeds maximum allowed size of {max_bytes} bytes.",
                "details": {"max_bytes": max_bytes}
            }
        }).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin1")),
                (b"x-content-type-options", b"nosniff"),
                (b"cache-control", b"no-store")
            ]
        })
        await send({
            "type": "http.response.body",
            "body": body
        })
