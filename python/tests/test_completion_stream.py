import asyncio
import json
import unittest

from retrievec.app.generation import ProviderError, completion_events


class CompletionStreamTests(unittest.TestCase):
    def read(self, parts):
        async def chunks():
            for part in parts:
                yield part

        async def collect():
            return [value async for value in completion_events(chunks())]

        return asyncio.run(collect())

    def test_fragmented_utf8_and_crlf_frames(self):
        values = [{"content": "α passage", "stop": False}, {"content": "", "stop": True}]
        wire = b": heartbeat\r\n\r\n" + b"".join(
            b"data: " + json.dumps(value, ensure_ascii=False).encode() + b"\r\n\r\n"
            for value in values
        )
        self.assertEqual(self.read([wire[i : i + 1] for i in range(len(wire))]), values)

    def test_incomplete_and_oversized_streams_fail(self):
        for parts in ([b'data: {"content":"unfinished"}'], [b"x" * (1024 * 1024 + 1)]):
            with self.assertRaises(ProviderError):
                self.read(parts)

    def test_invalid_json_and_nonobject_events_fail(self):
        for value in (b"[]", b"invalid"):
            with self.assertRaises(ValueError):
                self.read([b"data: " + value + b"\n\n"])
