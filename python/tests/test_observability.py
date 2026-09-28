import unittest

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from retrievec import observability


class TracingTests(unittest.TestCase):
    def test_parent_propagation_and_no_exception_or_baggage_export(self):
        previous = observability._provider
        observability._provider = None
        exporter = InMemorySpanExporter()
        observability.configure("test", exporter=exporter)
        try:
            parent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
            with observability.span(
                "http.test", incoming={"traceparent": parent, "baggage": "private"}
            ):
                with self.assertRaises(ValueError):
                    with observability.span("rpc.retrieval"):
                        outgoing = observability.carrier()
                        raise ValueError("private query and credential")
            self.assertEqual(set(outgoing), {"traceparent"})
            self.assertIn("a" * 32, outgoing["traceparent"])
            spans = exporter.get_finished_spans()
            self.assertEqual(len(spans), 2)
            self.assertEqual(spans[0].parent.span_id, spans[1].context.span_id)
            self.assertFalse(any(span.events for span in spans))
            self.assertNotIn("private", str([span.attributes for span in spans]))
        finally:
            observability._provider.shutdown()
            observability._provider = previous
