import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from retrievec.app.auth import COOKIE
from retrievec.app.config import Settings
from retrievec.app.main import create_app


class MemorySessions:
    def __init__(self):
        self.rows = {"valid": {"principal": "user-a", "csrf": "csrf-a"}}

    def load(self, token):
        return dict(self.rows.get(token, {}))

    def save(self, old, new, data):
        if old != new:
            self.rows.pop(old, None)
        if data:
            self.rows[new] = dict(data)

    def identity(self, issuer, subject):
        return "user-" + subject

    def consume(self, token):
        return self.rows.pop(token, {})


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.sessions = MemorySessions()
        self.app = create_app(Settings(dsn="unused", local_http=True), sessions=self.sessions)
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8000")

    def test_cookie_does_not_accept_principal_or_unknown_session(self):
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        self.client.cookies.set(COOKIE, "user-a")
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_csrf_and_logout_revoke_session(self):
        self.client.cookies.set(COOKIE, "valid")
        self.assertEqual(self.client.get("/api/v1/me").json()["principal_id"], "user-a")
        self.assertEqual(self.client.post("/auth/logout").status_code, 403)
        headers = {"Origin": "http://127.0.0.1:8000", "X-CSRF-Token": "csrf-a"}
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 200)
        self.client.cookies.set(COOKIE, "valid")
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_bad_callback_clears_flow(self):
        self.app.state.oidc.authorize_access_token = AsyncMock(side_effect=ValueError("bad state"))
        self.client.cookies.set(COOKIE, "valid")
        response = self.client.get("/auth/callback?code=fake&state=fake")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("valid", self.sessions.rows)

    def test_success_rotates_cookie_and_requires_verified_claims(self):
        self.sessions.rows["valid"]["_state_identity_state"] = {"data": {"nonce": "nonce"}}
        self.app.state.oidc.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {"sub": "b", "iss": self.app.state.settings.issuer, "nonce": "nonce"}
            }
        )
        self.client.cookies.set(COOKIE, "valid")
        response = self.client.get("/auth/callback?state=state", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertNotIn("valid", self.sessions.rows)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertNotIn("valid;", cookie)
