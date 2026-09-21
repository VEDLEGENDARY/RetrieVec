import asyncio
import io
import json
import logging
import unittest

from retrievec.telemetry import LOGGER, correlate, emit, request_identity


class TelemetryTests(unittest.TestCase):
    def test_private_fields_and_errors_never_enter_events(self):
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        old = LOGGER.level
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging.INFO)
        try:
            with correlate(request_id="a" * 32):
                emit(
                    "stage.finished",
                    prompt="private question",
                    token="credential",
                    text="paper",
                    error="server password",
                    elapsed_ms=float("nan"),
                    operation="search",
                    run_id="bad\nforged log",
                )
            event = json.loads(output.getvalue())
            self.assertEqual(event["request_id"], "a" * 32)
            self.assertEqual(event["operation"], "search")
            for forbidden in ("prompt", "token", "text", "error", "elapsed_ms", "run_id"):
                self.assertNotIn(forbidden, event)
        finally:
            LOGGER.removeHandler(handler)
            LOGGER.setLevel(old)

    def test_task_contexts_do_not_cross(self):
        from retrievec.telemetry import CONTEXT

        async def call(identity):
            with correlate(request_id=identity):
                await asyncio.sleep(0)
                return CONTEXT.get()["request_id"]

        async def both():
            return await asyncio.gather(call("a" * 32), call("b" * 32))

        self.assertEqual(asyncio.run(both()), ["a" * 32, "b" * 32])
        self.assertEqual(CONTEXT.get(), {})
        self.assertNotEqual(request_identity("private text"), "private text")
