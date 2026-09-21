"""ASGI correlation covers errors and response streaming without recording URLs."""

import time

from retrievec.telemetry import correlate, emit, request_identity


class RequestTelemetry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = dict(scope.get("headers", ())).get(b"x-request-id", b"")
        identity = request_identity(incoming.decode("ascii", errors="ignore"))
        scope.setdefault("state", {})["request_id"] = identity
        started, status = time.perf_counter(), 500

        async def correlated_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message = {
                    **message,
                    "headers": [
                        (name, value)
                        for name, value in message.get("headers", ())
                        if name.lower() != b"x-request-id"
                    ]
                    + [(b"x-request-id", identity.encode("ascii"))],
                }
            await send(message)

        with correlate(request_id=identity, service="application"):
            try:
                await self.app(scope, receive, correlated_send)
            finally:
                route = scope.get("route")
                emit(
                    "http.finished",
                    operation=getattr(route, "name", "unmatched"),
                    status_code=status,
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
