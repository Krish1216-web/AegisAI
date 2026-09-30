# ==============================================================================
# AegisAI Enterprise — Production Frontend Dockerfile (Context: frontend/)
# ==============================================================================

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./

RUN npm run build


FROM nginx:alpine-slim AS runtime

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
COPY ../docker/production/nginx.conf /etc/nginx/nginx.conf

RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx && \
    mkdir -p /tmp/client_temp /tmp/proxy_temp_path && \
    chown -R nginx:nginx /tmp

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
