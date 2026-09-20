import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.app.schemas import SearchInput


class ApplicationTests(unittest.TestCase):
    def test_http_exception_is_local_only(self):
        with self.assertRaises(ValueError):
            Settings(dsn="unused")
        with self.assertRaises(ValueError):
            Settings(dsn="unused", origin="http://example.com", local_http=True)

    def test_openapi_and_no_unprotected_resource_routes(self):
        client = TestClient(create_app(Settings(dsn="unused", local_http=True)))
        self.assertEqual(client.get("/healthz").status_code, 200)
        self.assertEqual(
            client.get("/api/v1/openapi.json").json()["info"]["title"], "RetrieVec workspace"
        )
        self.assertEqual(client.get("/api/v1/collections").status_code, 401)

    def test_search_modes_are_explicit(self):
        with self.assertRaises(ValidationError):
            SearchInput(collection_id="a", query="x AND y", mode="structured")
        with self.assertRaises(ValidationError):
            SearchInput(collection_id="a", query="x", candidates=1, top_k=10)
