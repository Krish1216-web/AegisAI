"""
Security headers ASGI middleware for AegisAI platform.
Enforces strict browser boundaries, CSP, framing defenses, permission policies,
and no-store caching on sensitive authentication and credential routes.
"""
from starlette.types import ASGIApp, Scope, Receive, Send
from app.core.config import settings

class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware that injects enterprise-grade HTTP security headers into all responses.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                header_map = {k.decode("latin1").lower(): v for k, v in headers}

                # 1. Prevent MIME Sniffing
                if "x-content-type-options" not in header_map:
                    headers.append((b"x-content-type-options", b"nosniff"))

                # 2. Clickjacking Defense
                if "x-frame-options" not in header_map:
                    headers.append((b"x-frame-options", b"DENY"))

                # 3. Referrer Policy
                if "referrer-policy" not in header_map:
                    headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))

                # 4. Permissions Policy
                if "permissions-policy" not in header_map:
                    headers.append((b"permissions-policy", b"geolocation=(), camera=(), microphone=(), payment=(), usb=()"))

                # 5. Content Security Policy (CSP)
                if "content-security-policy" not in header_map:
                    csp_val = (
                        b"default-src 'self'; "
                        b"script-src 'self' 'unsafe-inline'; "
                        b"style-src 'self' 'unsafe-inline'; "
                        b"img-src 'self' data: https:; "
                        b"font-src 'self' data:; "
                        b"connect-src 'self' ws: wss: http: https:; "
                        b"frame-ancestors 'none'; "
                        b"object-src 'none'; "
                        b"base-uri 'self'; "
                        b"form-action 'self';"
                    )
                    headers.append((b"content-security-policy", csp_val))

                # 6. HTTP Strict Transport Security (HSTS)
                if getattr(settings, "ENABLE_HSTS", False) and "strict-transport-security" not in header_map:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains; preload"))

                # 7. Sensitive route cache prevention (Auth, Admin, MCP Credentials)
                sensitive_prefixes = (
                    "/api/v1/auth",
                    "/api/v1/admin",
                    "/api/v1/mcp/credentials",
                )
                if any(path.startswith(sp) for sp in sensitive_prefixes):
                    headers = [(k, v) for k, v in headers if k.decode("latin1").lower() not in ("cache-control", "pragma")]
                    headers.append((b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"))
                    headers.append((b"pragma", b"no-cache"))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)
