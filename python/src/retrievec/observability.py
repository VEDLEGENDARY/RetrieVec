"""Opt-in OpenTelemetry spans with W3C context and no payload/exception capture."""

import atexit
import math
import os
from contextlib import contextmanager
from urllib.parse import urlsplit

_provider = None


def configure(service, *, exporter=None):
    global _provider
    if _provider is not None or (exporter is None and os.getenv("RETRIEVEC_OTEL") != "1"):
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    ratio = float(os.getenv("RETRIEVEC_OTEL_SAMPLE_RATIO", "0.1"))
    if not math.isfinite(ratio) or not 0 <= ratio <= 1:
        raise ValueError("trace sampling ratio must be between zero and one")
    testing = exporter is not None
    if exporter is None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = os.getenv("RETRIEVEC_OTEL_ENDPOINT", "http://127.0.0.1:4318/v1/traces")
        url = urlsplit(endpoint)
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("invalid trace collector endpoint")
        exporter = OTLPSpanExporter(endpoint=endpoint, timeout=2)
    provider = TracerProvider(
        resource=Resource.create({"service.name": service}),
        sampler=ParentBased(TraceIdRatioBased(1 if testing else ratio)),
    )
    provider.add_span_processor(
        SimpleSpanProcessor(exporter)
        if testing
        else BatchSpanProcessor(exporter, max_queue_size=2048, max_export_batch_size=256)
    )
    _provider = provider
    atexit.register(provider.shutdown)


def carrier():
    if _provider is None:
        return {}
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    headers = {}
    TraceContextTextMapPropagator().inject(headers)
    # Do not propagate baggage or vendor tracestate into another trust boundary.
    return {key: value for key, value in headers.items() if key == "traceparent"}


@contextmanager
def span(name, *, incoming=None):
    if _provider is None:
        yield None
        return
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    context = None
    if incoming is not None:
        context = TraceContextTextMapPropagator().extract(
            {"traceparent": incoming.get("traceparent", "")}
        )
    with _provider.get_tracer("retrievec").start_as_current_span(
        name,
        context=context,
        record_exception=False,
        set_status_on_exception=False,
    ) as current:
        try:
            yield current
        except BaseException:
            current.set_status(Status(StatusCode.ERROR))
            raise
