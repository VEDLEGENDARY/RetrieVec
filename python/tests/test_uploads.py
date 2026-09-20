import asyncio
import io
import tempfile
import unittest
from pathlib import Path

from retrievec.app.config import Settings
from retrievec.app.main import APIError
from retrievec.app.uploads import display_name, stage_file
from retrievec.corpus.importer import CorpusError, extract_pages
from starlette.datastructures import UploadFile


class UploadTests(unittest.TestCase):
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
