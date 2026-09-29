import json
import runpy
import unittest
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import ValidationError
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.app.schemas import SearchInput


class ApplicationTests(unittest.TestCase):
    def test_unexpected_failure_keeps_correlation_without_private_details(self):
        app = create_app(Settings(dsn="unused", local_http=True))

        def broken():
            raise RuntimeError("private evidence and credentials")

        app.router.routes.insert(0, APIRoute("/broken", broken))
        client = TestClient(app, raise_server_exceptions=False)
        with self.assertLogs("retrievec.events", level="INFO") as logs:
            response = client.get("/broken", headers={"X-Request-ID": "b" * 32})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers.get("x-request-id"), "b" * 32)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("private evidence", response.text)
        event = json.loads(logs.records[-1].getMessage())
        self.assertEqual(event["status_code"], response.status_code)
        self.assertEqual(event["request_id"], response.headers["x-request-id"])
        self.assertNotIn("private evidence", logs.output[0])

    def test_module_entry_point_uses_the_same_error_contract(self):
        created = []
        with (
            patch.dict("os.environ", {"RETRIEVEC_DSN": "unused", "RETRIEVEC_LOCAL_HTTP": "1"}),
            patch("uvicorn.run", side_effect=lambda app, **kwargs: created.append(app)),
        ):
            runpy.run_module("retrievec.app.main", run_name="__main__")
        response = TestClient(created[0]).get("/api/v1/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "unauthenticated")

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
