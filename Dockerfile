# syntax=docker/dockerfile:1.7
FROM node:24.14.0-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM golang:1.26.8-bookworm AS engine
WORKDIR /src/engine
COPY engine/go.mod engine/go.sum ./
RUN go mod download
COPY engine/ ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/retrievald ./cmd/retrievald

FROM python:3.13.15-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RETRIEVEC_HOST=0.0.0.0 \
    RETRIEVEC_PORT=8000 \
    RETRIEVEC_STORE=/app/artifacts/store \
    RETRIEVEC_RPC=127.0.0.1:8092 \
    RETRIEVEC_ENGINE=/usr/local/bin/retrievald \
    RETRIEVEC_FRONTEND=/app/web/dist \
    HF_HOME=/app/artifacts/cache/huggingface
WORKDIR /app
RUN groupadd --gid 10001 retrievec && useradd --uid 10001 --gid retrievec --home /app retrievec
COPY python/pyproject.toml /tmp/retrievec/pyproject.toml
COPY python/src /tmp/retrievec/src
RUN pip install --no-cache-dir '/tmp/retrievec[app,telemetry]' && rm -rf /tmp/retrievec
COPY --from=engine /out/retrievald /usr/local/bin/retrievald
COPY --from=web /src/web/dist /app/web/dist
COPY configs /app/configs
COPY demo /app/demo
COPY datasets/answer_quality /app/datasets/answer_quality
COPY docker/entrypoint.sh /usr/local/bin/retrievec-entrypoint
RUN chmod +x /usr/local/bin/retrievec-entrypoint && mkdir -p /app/artifacts/store /app/artifacts/cache && chown -R retrievec:retrievec /app
USER retrievec
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
ENTRYPOINT ["/bin/sh", "/usr/local/bin/retrievec-entrypoint"]
CMD ["workspace"]
