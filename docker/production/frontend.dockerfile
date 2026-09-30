# ==============================================================================
# AegisAI Enterprise — Production Frontend Dockerfile (Multi-Stage Build)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend Assets
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies deterministically
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Production build via Vite
RUN npm run build


# ------------------------------------------------------------------------------
# Stage 2: Production Nginx Server
# ------------------------------------------------------------------------------
FROM nginx:alpine-slim AS runtime

# Remove default nginx html
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy optimized reverse proxy nginx config
COPY docker/production/nginx.conf /etc/nginx/nginx.conf

# Set permissions for non-root runtime
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx && \
    mkdir -p /tmp/client_temp /tmp/proxy_temp_path && \
    chown -R nginx:nginx /tmp

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
