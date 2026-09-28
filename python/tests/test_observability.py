import os
import unittest
import uuid

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

    @unittest.skipUnless(os.getenv("RETRIEVEC_TEST_DSN"), "requires isolated PostgreSQL 18")
    def test_queue_context_survives_idempotent_retry_and_claim(self):
        from retrievec.registry.database import Registry
        from retrievec.registry.jobs import Jobs

        registry = Registry(os.environ["RETRIEVEC_TEST_DSN"])
        registry.migrate()
        owner, collection = "trace-" + uuid.uuid4().hex, "trace-" + uuid.uuid4().hex
        registry.create_collection(owner, collection)
        jobs = Jobs(registry, owner)
        previous = observability._provider
        observability._provider = None
        exporter = InMemorySpanExporter()
        observability.configure("test", exporter=exporter)
        try:
            with observability.span("enqueue"):
                expected = observability.carrier()["traceparent"]
                created = jobs.enqueue(collection, "once", {}, {})
            with observability.span("retry"):
                replay = jobs.enqueue(collection, "once", {}, {})
            self.assertEqual(created["job_id"], replay["job_id"])
            self.assertEqual(replay["traceparent"], expected)
            claimed = jobs.claim()
            self.assertEqual(claimed["traceparent"], expected)
            with observability.span(
                "ingestion.job", incoming={"traceparent": claimed["traceparent"]}
            ):
                self.assertEqual(
                    observability.carrier()["traceparent"].split("-")[1], expected.split("-")[1]
                )
        finally:
            observability._provider.shutdown()
            observability._provider = previous
