import argparse
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from retrievec.evaluation.load import execute
from retrievec.evaluation.load_recovery import recover


class LoadExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        session, queries = self.root / "session.json", self.root / "queries.json"
        session.write_text(
            json.dumps(
                {"session_cookie": "private-session-token", "csrf_token": "private-csrf-token"}
            )
        )
        queries.write_text(json.dumps(["private question text"]))
        self.args = argparse.Namespace(
            origin="http://127.0.0.1:8000",
            profile="concurrent-search",
            concurrency=1,
            requests=3,
            warmup=0,
            timeout=10,
            wall_seconds=30,
            corpus_size=12,
            allow_mutations=False,
            slow_provider_confirmed=False,
            session=session,
            queries=queries,
            output=self.root / "run",
            collection="fixture",
            provider="local",
            configuration_note="synthetic transport test",
        )

    async def test_transport_failure_and_overload_are_in_denominator(self):
        calls = []

        async def handler(request):
            calls.append(request.headers["x-request-id"])
            if len(calls) == 2:
                raise httpx.ConnectError("private transport details", request=request)
            if len(calls) == 3:
                return httpx.Response(503, json={"message": "busy"})
            return httpx.Response(
                200,
                json={
                    "snapshot_id": "rs_" + "a" * 64,
                    "results": {"sparse": {"timings": {"search_ms": 1}}},
                },
            )

        report = await execute(self.args, transport=httpx.MockTransport(handler))
        self.assertEqual(report["results"]["request_count"], 3)
        self.assertEqual(report["results"]["successes"], 1)
        self.assertEqual(report["results"]["errors"], {"transport": 1, "http_503": 1})
        self.assertEqual(len(set(calls)), 3)
        recovered = recover(self.args.output)
        self.assertEqual(recovered["measured"]["never_started"], 0)
        self.assertEqual(recovered["measured"]["unknown_outcomes"], [])
        captured = "".join(path.read_text() for path in self.args.output.iterdir())
        for secret in (
            "private-session-token",
            "private-csrf-token",
            "private question text",
            "private transport details",
        ):
            self.assertNotIn(secret, captured)

    async def test_interruption_is_journaled_without_success_claim(self):
        entered, blocked = asyncio.Event(), asyncio.Event()

        async def handler(request):
            entered.set()
            await blocked.wait()
            return httpx.Response(200, json={})

        task = asyncio.create_task(execute(self.args, transport=httpx.MockTransport(handler)))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        result = recover(self.args.output)
        self.assertFalse(result["completion_report_present"])
        self.assertEqual(result["measured"]["never_started"], 2)
        self.assertEqual(result["measured"]["recorded"]["successes"], 0)
        self.assertEqual(result["measured"]["recorded"]["errors"], {"interrupted": 1})
