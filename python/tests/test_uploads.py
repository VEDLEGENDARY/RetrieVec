import asyncio
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient
from retrievec.app.auth import COOKIE
from retrievec.app.config import Settings
from retrievec.app.main import APIError, create_app
from retrievec.app.uploads import display_name, stage_file
from retrievec.corpus.importer import CorpusError, extract_pages
from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from starlette.datastructures import UploadFile
from test_auth import MemorySessions


class UploadTests(unittest.TestCase):
    def test_uncertain_database_commit_retains_original_for_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(dsn="unused", local_http=True, store=Path(directory))
            registry = SimpleNamespace(
                connect=lambda: nullcontext(None), authorize=lambda *args, **kwargs: {}
            )
            client = TestClient(create_app(settings, registry=registry, sessions=MemorySessions()))
            client.cookies.set(COOKIE, "valid")
            with patch(
                "retrievec.app.uploads.enqueue_uploads", side_effect=psycopg.OperationalError
            ):
                response = client.post(
                    "/api/v1/collections/owned/uploads",
                    files={"files": ("paper.txt", b"Private original")},
                    headers={
                        "Origin": settings.origin,
                        "X-CSRF-Token": "csrf-a",
                        "Idempotency-Key": "once",
                    },
                )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["code"], "upload_unconfirmed")
            originals = list((settings.store / "sources").iterdir())
            self.assertEqual(len(originals), 1)
            self.assertEqual(originals[0].read_bytes(), b"Private original")

    @unittest.skipUnless(os.getenv("RETRIEVEC_ENGINE"), "requires the built analyzer")
    def test_private_extraction_runs_with_real_analyzer_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources").mkdir()
            raw = b"Dense retrieval provides semantic matching."
            (root / "sources" / "paper.txt").write_bytes(raw)
            manifest = root / "manifest.json"
            manifest.write_bytes(
                canonical(
                    {
                        "schema_version": 1,
                        "sources": [
                            {
                                "paper_id": "paper",
                                "title": "Paper",
                                "authors": [],
                                "path": "paper.txt",
                                "source_url": None,
                                "source_sha256": digest(raw),
                                "license_note": "Test text",
                            }
                        ],
                    }
                )
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "retrievec.app.extract",
                    str(manifest),
                    str(root),
                    "private-test",
                    os.environ["RETRIEVEC_ENGINE"],
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            _, _, chunks = load_snapshot(root / "corpora" / result.stdout.strip())
            self.assertEqual(chunks[0]["text"], raw.decode())

    def test_extraction_process_can_enforce_resource_limits(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from retrievec.app.process_limits import limit_extraction; "
                "limit_extraction(); print('limited')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "limited")

    def test_signature_size_and_path_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                dsn="unused", local_http=True, store=Path(directory), max_file_bytes=12
            )
            for name, content in [
                ("hostile.pdf", b"not a pdf"),
                ("big.txt", b"a" * 13),
                ("code.exe", b"MZ"),
                ("empty.txt", b""),
            ]:
                with self.subTest(name=name), self.assertRaises(APIError):
                    asyncio.run(
                        stage_file(UploadFile(io.BytesIO(content), filename=name), settings)
                    )
            self.assertEqual(list((settings.store / "sources").iterdir()), [])
            row = asyncio.run(
                stage_file(UploadFile(io.BytesIO(b"text"), filename="../../x.txt"), settings)
            )
            self.assertNotIn("/", row["storage_key"])
            self.assertNotIn("..", row["storage_key"])
            self.assertNotIn("/", display_name("../../x.txt"))
            self.assertEqual(
                (settings.store / "sources" / row["storage_key"]).read_bytes(), b"text"
            )

    def test_pdf_page_limit_and_encryption(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaises(CorpusError):
            extract_pages(Path("paper.pdf"), stream.getvalue(), max_pages=1)
        writer.encrypt("test-password")
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaises(CorpusError):
            extract_pages(Path("paper.pdf"), stream.getvalue())
