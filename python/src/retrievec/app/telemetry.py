"""ASGI correlation covers errors and response streaming without recording URLs."""

import time

from retrievec.observability import span
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
        response_started = False

        async def correlated_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
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

        incoming_trace = dict(scope.get("headers", ())).get(b"traceparent", b"")
        with (
            span(
                "http.request",
                incoming={"traceparent": incoming_trace.decode("ascii", errors="ignore")},
            ) as current,
            correlate(request_id=identity, service="application"),
        ):
            try:
                await self.app(scope, receive, correlated_send)
            except Exception:
                # The outer application error handler returns a safe 503 envelope.
                # Streaming responses retain the status already sent to the client.
                if not response_started:
                    status = 503
                raise
            finally:
                route = scope.get("route")
                if current is not None:
                    current.update_name("http." + getattr(route, "name", "unmatched"))
                    current.set_attribute("http.response.status_code", status)
                emit(
                    "http.finished",
                    operation=getattr(route, "name", "unmatched"),
                    status_code=status,
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
