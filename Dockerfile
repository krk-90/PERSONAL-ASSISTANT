FROM node:22-alpine AS frontend-build

WORKDIR /build/app/frontend
COPY app/frontend/package*.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001 \
    MCP_TRANSPORT=streamable-http

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY agent ./agent
COPY llm_gateway ./llm_gateway
COPY mcp_server ./mcp_server
COPY supabase ./supabase
COPY --from=frontend-build /build/app/frontend/dist ./app/frontend/dist
COPY docker/supervisord.conf /etc/supervisor/conf.d/personal-assistant.conf
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]