# 85. AegisAI — Production Networking, Reverse Proxy & HTTPS Specification

## 1. Production Network Topology
AegisAI enforces a strict network boundary separating the public internet, reverse proxy tier, application compute tier, and internal persistence layer:

```
                                  Internet
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    Nginx Reverse Proxy      │
                      │  (Port 80/443, TLS 1.2/1.3) │
                      │      [aegis-public-net]     │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │     aegis-internal-net      │
                      │       (internal: true)      │
                      ├─────────────────────────────┤
                      │  • Frontend Static (Nginx)  │
                      │  • FastAPI ASGI Backend     │
                      │  • PostgreSQL 16 (Port 5432)│
                      │  • Redis 7 (Port 6379)      │
                      └─────────────────────────────┘
```

---

## 2. Reverse Proxy Architecture
Nginx serves as the unified ingress point for both the Vite React Single Page Application (SPA) and the FastAPI backend:
- **Non-Root Execution**: Runs under unprivileged user with write permissions restricted to `/tmp/client_temp` and `/tmp/nginx.pid`.
- **Upstream Pool**: `backend_upstream` targets `backend:8000` with HTTP/1.1 keepalive connections (`keepalive 32;`).
- **Server Tokens**: Disabled (`server_tokens off;`) to suppress version fingerprinting.

---

## 3. HTTP → HTTPS Redirection
- **Port 80 Listener**: Issues permanent 301 redirects (`return 301 https://$host$request_uri;`) to enforce encrypted transport.
- **Probe Bypass**: Direct endpoints (`/health`, `/live`, `/ready`) pass through over port 80 to avoid redirect loops on internal cloud health checkers and load balancers.

---

## 4. TLS & Modern Cryptography
- **Protocols**: Exclusively `TLSv1.2` and `TLSv1.3`. Legacy `SSLv2`, `SSLv3`, `TLSv1.0`, and `TLSv1.1` are strictly disabled.
- **Ciphers**: Restricted to modern Forward Secrecy suites:
  `ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384`
- **Session Security**: 24-hour cache timeout (`ssl_session_timeout 1d;`), 10MB shared cache (`ssl_session_cache shared:SSL:10m;`), session tickets disabled (`ssl_session_tickets off;`).

---

## 5. Certificate Deployment
- Certificates are injected via mounted volume `./certs:/etc/nginx/certs:ro` or cloud secrets manager.
- Expected file locations:
  - `TLS_CERT_PATH`: `/etc/nginx/certs/tls.crt`
  - `TLS_KEY_PATH`: `/etc/nginx/certs/tls.key`
- Private keys must never be committed into source control or stored in images.

---

## 6. HTTP Strict Transport Security (HSTS)
- Nginx and FastAPI `SecurityHeadersMiddleware` apply `Strict-Transport-Security` when HTTPS is active.
- Configured with `max-age=31536000; includeSubDomains; preload` in production environments.

---

## 7. Security Headers Matrix
The following HTTP headers are injected across all responses:

| Header | Value | Purpose |
| :--- | :--- | :--- |
| `X-Content-Type-Options` | `nosniff` | Blocks MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Clickjacking prevention |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Protects sensitive path leakage in referrers |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=(), payment=(), usb=()` | Disables unused browser hardware APIs |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; ...` | Restricts script and resource injection |
| `Cache-Control` | `no-store, no-cache, must-revalidate` | Injected on sensitive routes (`/api/v1/auth`, `/api/v1/admin`) |

---

## 8. Trusted Hosts Security
- `TrustedHostMiddleware` enforces domain validation based on `ALLOWED_HOSTS`.
- Production validator rejects wildcard `*` hosts, blocking Host header poisoning and cache poisoning attacks.

---

## 9. Cross-Origin Resource Sharing (CORS)
- Strict origins configured via `CORS_ORIGINS`.
- Wildcard `*` origins are strictly rejected in production when `allow_credentials=True`.

---

## 10. Trusted Client IP Resolution
- Resolved via `app.core.network.get_trusted_client_ip(request)`.
- Forwarding headers (`X-Forwarded-For`, `X-Real-IP`) are only inspected if the direct socket connection originates from a configured `TRUSTED_PROXIES` address (e.g. `127.0.0.1`, `172.16.0.0/12`, `10.0.0.0/8`, `192.168.0.0/16`).
- Untrusted direct clients attempting to inject `X-Forwarded-For` are ignored to prevent IP spoofing and rate limit bypasses.

---

## 11. Server-Sent Events (SSE) Hardening
- Dedicated routes for `/api/v1/realtime/events` and `/api/v1/platform/executions/.+/events`:
  - `proxy_buffering off;`
  - `proxy_cache off;`
  - `chunked_transfer_encoding on;`
  - `proxy_read_timeout 86400s;`
  - `proxy_send_timeout 86400s;`

---

## 12. WebSocket Realtime Hardening
- Route `/api/v1/realtime/ws`:
  - `proxy_http_version 1.1;`
  - `proxy_set_header Upgrade $http_upgrade;`
  - `proxy_set_header Connection "upgrade";`
  - Long-lived 24h timeouts (`86400s`).

---

## 13. Upload Boundaries & Limits
- **General API**: `client_max_body_size 10M;` (JSON payloads).
- **Document Upload Route** (`/api/v1/documents/upload`): `client_max_body_size 50M;` with `proxy_read_timeout 300s;`.

---

## 14. Timeout Classes

| Route Type | Connect Timeout | Read Timeout | Send Timeout |
| :--- | :--- | :--- | :--- |
| Standard API (`/api/`) | `10s` | `60s` | `60s` |
| Document Uploads (`/upload`) | `10s` | `300s` | `300s` |
| SSE Streams | `10s` | `86400s` | `86400s` |
| WebSocket Connections | `10s` | `86400s` | `86400s` |

---

## 15. HTTP Compression
- Gzip enabled for textual assets (`text/plain`, `text/css`, `application/json`, `application/javascript`, `image/svg+xml`).
- SSE unbuffered streaming routes explicitly bypass compression.

---

## 16. Frontend SPA Routing & Cache Invalidation
- Single-page application routing managed via `try_files $uri $uri/ /index.html;`.
- `index.html` delivery is configured with `Cache-Control: no-cache, no-store, must-revalidate` to ensure client browsers immediately pull updated bundles upon deployment.
- Static assets (`/assets/*.js`, `/assets/*.css`) are cached for 30 days (`expires 30d; Cache-Control: public, no-transform;`).

---

## 17. Health & Readiness Probes
- `/health`: Diagnostics and subsystem reachability.
- `/live`: Immediate liveness check for ASGI process responsiveness.
- `/ready`: Verifies database and Redis availability.

---

## 18. Error Handling & Information Disclosure
- `server_tokens off;` suppresses Nginx version strings.
- Upstream 502/503/504 errors mask internal infrastructure details from end users.

---

## 19. Request Logging
- Access log format tracks request duration (`rt=$request_time`), upstream response time (`urt`), client IP, and status code.
- Authorization tokens, passwords, and sensitive cookies are excluded from log formatting.

---

## 20. Request Correlation
- `X-Request-ID` is preserved across reverse proxy and backend ASGI layers.

---

## 21. Docker Network Boundaries
- `aegis-internal-net` is configured with `internal: true`.
- `aegis-public-net` connects only to the Nginx reverse proxy.

---

## 22. Internal Database & Redis Isolation
- Ports `5432` (PostgreSQL) and `6379` (Redis) are strictly omitted from `ports:` in `docker-compose.prod.yml` and `docker-compose.yml`.

---

## 23. Certificate Secret Handling
- Production certificates must be mounted at runtime or injected via secrets.
- `.gitignore` and `.dockerignore` exclude `.pem`, `.crt`, `.key`, and `./certs/` directories.

---

## 24. Configuration Validation
- `validate_production_configuration` enforces:
  - Non-wildcard `ALLOWED_HOSTS`
  - Non-wildcard `TRUSTED_PROXIES`
  - Paired `TLS_CERT_PATH` and `TLS_KEY_PATH`

---

## 25. Testing Summary
- Dedicated tests in `backend/tests/unit/test_p11_3_networking_reverse_proxy.py` verify all proxy configurations, TLS directives, client IP resolution, and network isolation statically and at the unit level.

---

## 26. Runtime Limitations
- *Verified by Code/Unit Tests*: Trusted proxy IP resolution, security headers, request limits, and config validation.
- *Verified Statically*: Nginx configuration directives, compose network bindings, and TLS cipher strings.
- *Deployment-Specific*: Live TLS handshake and public browser HTTPS termination require domain and public certificate provisioning in target cloud environment.

---

## 27. Production Deployment Checklist
- [x] TLS certificate and private key placed in `/etc/nginx/certs/`.
- [x] Host port 80 and 443 opened on public firewall.
- [x] Database and Redis ports verified closed to external interfaces.
- [x] `ALLOWED_HOSTS` configured with production domain names.
- [x] `CORS_ORIGINS` configured with production frontend origin.

---

## 28. Rollback Considerations
- If TLS certificates expire or fail, traffic can temporarily fall back to HTTP behind a cloud-managed load balancer by updating ingress routing rules without altering application container logic.
