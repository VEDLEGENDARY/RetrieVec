import os
import unittest
import uuid

from fastapi.testclient import TestClient
from retrievec.app.auth import COOKIE, Sessions
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.registry.database import Registry


@unittest.skipUnless(os.getenv("RETRIEVEC_TEST_DSN"), "requires isolated PostgreSQL 18")
class WorkspaceDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(os.environ["RETRIEVEC_TEST_DSN"])
        self.registry.migrate()
        self.sessions = Sessions(self.registry)
        suffix = uuid.uuid4().hex
        self.a = self.sessions.identity("test-issuer", "a" + suffix)
        self.b = self.sessions.identity("test-issuer", "b" + suffix)
        self.sessions.save("", "a" + suffix, {"principal": self.a, "csrf": "csrf"})
        self.sessions.save("", "b" + suffix, {"principal": self.b, "csrf": "csrf"})
        self.app = create_app(Settings(dsn=self.registry.dsn, local_http=True))
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8000")
        self.tokens = {self.a: "a" + suffix, self.b: "b" + suffix}
        self.headers = {"Origin": "http://127.0.0.1:8000", "X-CSRF-Token": "csrf"}

    def user(self, user):
        self.client.cookies.clear()
        self.client.cookies.set(COOKIE, self.tokens[user])

    def test_private_curated_and_archive_policy(self):
        self.user(self.a)
        response = self.client.post(
            "/api/v1/collections", json={"title": "Private"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 201, response.text)
        collection = response.json()["collection_id"]
        self.user(self.b)
        ids = [r["collection_id"] for r in self.client.get("/api/v1/collections").json()]
        self.assertNotIn(collection, ids)
        self.assertEqual(
            self.client.patch(
                "/api/v1/collections/" + collection, json={"title": "stolen"}, headers=self.headers
            ).status_code,
            404,
        )
        with self.registry.connect() as db:
            db.execute(
                "UPDATE collections SET visibility='curated' WHERE collection_id=%s", (collection,)
            )
        visible = self.client.get("/api/v1/collections").json()
        self.assertFalse(next(r for r in visible if r["collection_id"] == collection)["can_manage"])
        self.assertEqual(
            self.client.delete(
                "/api/v1/collections/" + collection, headers=self.headers
            ).status_code,
            404,
        )
        self.user(self.a)
        self.assertEqual(
            self.client.delete(
                "/api/v1/collections/" + collection, headers=self.headers
            ).status_code,
            204,
        )
        with self.registry.connect() as db, self.assertRaises(PermissionError):
            self.registry.authorize(db, self.a, collection)

    def test_session_expiry_and_no_resurrection(self):
        token = self.tokens[self.a]
        self.sessions.save(token, "", {})
        self.sessions.save(token, token, {"principal": self.a})
        self.assertEqual(self.sessions.load(token), {})
        self.assertEqual(self.sessions.identity("test-issuer", "a" + token[1:]), self.a)
