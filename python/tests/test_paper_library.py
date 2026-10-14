"""Library contract, query bounds, and live authorization without external services."""

import unittest
from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from retrievec.app.auth import COOKIE
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from test_auth import MemorySessions


class PaperLibraryTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.registry = SimpleNamespace(
            connect=lambda: nullcontext(self.db), authorize=Mock(return_value={})
        )
        self.client = TestClient(
            create_app(
                Settings(dsn="unused", local_http=True),
                registry=self.registry,
                sessions=MemorySessions(),
            )
        )
        self.route = "/api/v1/collections/owned/papers"

    def test_authentication_and_authorization_precede_filename_queries(self):
        self.assertEqual(self.client.get(self.route).status_code, 401)
        self.registry.authorize.assert_not_called()
        self.client.cookies.set(COOKIE, "valid")
        self.registry.authorize.side_effect = PermissionError("unavailable")
        self.assertEqual(self.client.get(self.route).status_code, 404)
        self.registry.authorize.assert_called_once_with(
            self.db, "user-a", "owned", read=True, lock=False
        )
        self.db.execute.assert_not_called()

    def test_response_and_parameterized_literal_search(self):
        self.client.cookies.set(COOKIE, "valid")
        row = {
            "source_id": "11111111-1111-4111-8111-111111111111",
            "display_name": "Study.pdf",
            "media_type": "application/pdf",
            "size_bytes": 2048,
            "created_at": datetime(2026, 10, 14, tzinfo=UTC),
            "state": "queued",
        }
        self.db.execute.return_value = SimpleNamespace(fetchall=lambda: [row, row])
        query = "%_' OR 1=1"
        cursor = "2026-10-15T00:00:00+00:00|11111111-1111-4111-8111-111111111111"
        response = self.client.get(self.route, params={"q": query, "limit": 1, "after": cursor})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(result["next_cursor"].endswith("|" + row["source_id"]))
        self.assertEqual(set(result["items"][0]), set(row))
        self.assertEqual(result["items"][0]["state"], "queued")
        for call in self.db.execute.call_args_list:
            sql, parameters = call.args
            self.assertNotIn(query, sql)
            self.assertIn("strpos", sql)
            self.assertEqual(parameters[:2], ("owned", query))
        self.assertIn("s.created_at DESC,s.source_id DESC", self.db.execute.call_args.args[0])
        self.assertIn("(s.created_at,s.source_id)<(%s,%s)", self.db.execute.call_args.args[0])
        self.assertNotIn("OFFSET", self.db.execute.call_args.args[0])
        self.assertEqual(self.db.execute.call_args.args[1][-1], 2)

    def test_empty_and_final_pages_do_not_return_a_cursor(self):
        self.client.cookies.set(COOKIE, "valid")
        self.db.execute.return_value = SimpleNamespace(fetchall=lambda: [])
        response = self.client.get(self.route)
        self.assertEqual(response.json(), {"items": [], "next_cursor": None})

    def test_invalid_pagination_and_search_never_query_the_database(self):
        self.client.cookies.set(COOKIE, "valid")
        for params in (
            {"limit": 0},
            {"limit": 51},
            {"after": "invalid"},
            {"after": "2026-10-14|11111111-1111-4111-8111-111111111111"},
            {"after": "2026-10-14T00:00:00Z|invalid"},
            {"after": "x" * 97},
            {"q": "x" * 121},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.route, params=params).status_code, 422)
        self.db.execute.assert_not_called()
