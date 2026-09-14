import json
import os
import queue
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from retrievallab.client.capture import capture
from retrievallab.client.http import Client, RetrievalError

ROOT = Path(__file__).resolve().parents[2]


class ClientTests(unittest.TestCase):
    def test_live_service_and_repeated_capture(self):
        engine = os.environ.get("RETRIEVALLAB_ENGINE")
        self.assertIsNotNone(engine, "shared checks must build the real service")
        snapshot = next((ROOT / "datasets/fixtures/snapshots").iterdir())
        process = subprocess.Popen(
            [engine, "--corpus", str(snapshot), "--listen", "127.0.0.1:0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        lines = queue.Queue()
        reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            line = lines.get(timeout=20).strip()
            self.assertTrue(line.startswith("listening http://"), line)
            client = Client(line.removeprefix("listening "))
            self.assertGreater(client.search("retrieval", explain=True)["total_matches"], 0)
            with self.assertRaises(RetrievalError) as caught:
                client.search("red AND", mode="structured")
            self.assertEqual(caught.exception.status, 400)
            with tempfile.TemporaryDirectory() as directory:
                queries = ROOT / "datasets/fixtures/queries-v1.jsonl"
                first = capture(client, queries, Path(directory) / "first")
                second = capture(client, queries, Path(directory) / "second")
                self.assertEqual(first["ranking_sha256"], second["ranking_sha256"])
                self.assertEqual(first["error_count"], 1)
                rows = [
                    json.loads(line)
                    for line in (Path(directory) / "first/results.jsonl").read_text().splitlines()
                ]
                self.assertEqual(rows[-1]["error"]["code"], "invalid_query")
        finally:
            process.terminate()
            process.communicate(timeout=10)
            reader.join(timeout=2)

    def test_response_validation_and_transport_errors(self):
        client = Client()
        with patch.object(client, "_request", return_value={}), self.assertRaises(RetrievalError):
            client.search("red")
        with (
            patch("retrievallab.client.http.urlopen", side_effect=TimeoutError),
            self.assertRaises(RetrievalError) as caught,
        ):
            client.search("red")
        self.assertEqual(caught.exception.code, "transport_error")
