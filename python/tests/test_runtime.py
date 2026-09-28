import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.runtime import supervise


class RuntimeTests(unittest.TestCase):
    def test_installed_frontend_path_is_served(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("installed workspace", encoding="utf-8")
            app = create_app(Settings(dsn="unused", local_http=True, frontend=root))
            self.assertEqual(TestClient(app).get("/").text, "installed workspace")

    def test_missing_explicit_frontend_fails_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                create_app(Settings(dsn="unused", local_http=True, frontend=Path(directory)))

    def test_database_outage_affects_readiness_only(self):
        app = create_app(Settings(dsn="host=127.0.0.1 port=1 dbname=unavailable", local_http=True))
        client = TestClient(app)
        self.assertEqual(client.get("/healthz").status_code, 200)
        response = client.get("/readyz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_unexpected_successful_child_exit_fails_supervisor(self):
        self.assertEqual(supervise([[sys.executable, "-c", "pass"]], grace_seconds=1), 1)

    def test_failed_child_stops_live_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "pid"
            # The first child waits for the sibling to start, avoiding a timing assumption.
            watcher = (
                "import pathlib,time; "
                f"p=pathlib.Path({str(marker)!r}); "
                "exec('while not p.exists(): time.sleep(0.01)'); raise SystemExit(7)"
            )
            sibling = (
                "import os,pathlib,time; "
                f"pathlib.Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)"
            )
            roles = [[sys.executable, "-c", watcher], [sys.executable, "-c", sibling]]
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from retrievec.runtime import supervise; "
                    f"raise SystemExit(supervise({roles!r}, grace_seconds=1))",
                ],
                timeout=10,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            if os.name != "nt":
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(marker.read_text()), 0)
