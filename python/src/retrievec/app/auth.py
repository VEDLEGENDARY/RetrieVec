"""OIDC through Authlib; opaque, revocable server-side browser sessions."""

import hashlib
import secrets
import uuid
from urllib.parse import urlsplit

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

COOKIE = "retrievec_session"


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Sessions:
    def __init__(self, registry):
        self.registry = registry

    def load(self, token):
        with self.registry.connect() as db:
            row = db.execute(
                "SELECT data FROM browser_sessions WHERE token_hash=%s "
                "AND expires_at>clock_timestamp()",
                (token_hash(token),),
            ).fetchone()
            return row["data"] if row else {}

    def save(self, old_token, new_token, data):
        with self.registry.connect() as db:
            db.execute("DELETE FROM browser_sessions WHERE expires_at<clock_timestamp()")
            if old_token != new_token:
                if old_token:
                    db.execute(
                        "DELETE FROM browser_sessions WHERE token_hash=%s", (token_hash(old_token),)
                    )
                if data:
                    db.execute(
                        "INSERT INTO browser_sessions VALUES(%s,%s,clock_timestamp()+"
                        "(%s * interval '1 second'))",
                        (
                            token_hash(new_token),
                            Jsonb(data),
                            28800 if data.get("principal") else 600,
                        ),
                    )
            elif data:
                # Updates never resurrect a session invalidated by a concurrent logout.
                db.execute(
                    "UPDATE browser_sessions SET data=%s WHERE token_hash=%s "
                    "AND expires_at>clock_timestamp()",
                    (Jsonb(data), token_hash(old_token)),
                )

    def consume(self, token):
        with self.registry.connect() as db:
            row = db.execute(
                "DELETE FROM browser_sessions WHERE token_hash=%s "
                "AND expires_at>clock_timestamp() RETURNING data",
                (token_hash(token),),
            ).fetchone()
            return row["data"] if row else {}

    def identity(self, issuer, subject):
        with self.registry.connect() as db:
            db.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (issuer + "\n" + subject,)
            )
            row = db.execute(
                "SELECT principal_id FROM identities WHERE issuer=%s AND subject=%s",
                (issuer, subject),
            ).fetchone()
            if row:
                return row["principal_id"]
            principal = "user_" + uuid.uuid4().hex
            db.execute("INSERT INTO principals VALUES(%s)", (principal,))
            db.execute("INSERT INTO identities VALUES(%s,%s,%s)", (issuer, subject, principal))
            return principal


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, sessions, settings):
        super().__init__(app)
        self.sessions, self.settings = sessions, settings

    async def dispatch(self, request, call_next):
        token = request.cookies.get(COOKIE, "")
        if len(token) > 128:
            token = ""
        data = await run_in_threadpool(self.sessions.load, token) if token else {}
        original = dict(data)
        request.scope["session"] = data
        request.state.rotate_session = False
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("x-csrf-token", "")
            expected = data.get("csrf", "")
            if (
                request.headers.get("origin") != self.settings.origin
                or not expected
                or not secrets.compare_digest(supplied, expected)
            ):
                return JSONResponse(
                    {"code": "csrf_failed", "message": "Refresh your session"}, status_code=403
                )
        response = await call_next(request)
        if data != original or request.state.rotate_session:
            rotate = request.state.rotate_session or not original
            new_token = secrets.token_urlsafe(32) if rotate else token
            await run_in_threadpool(self.sessions.save, token, new_token, data)
            if data:
                response.set_cookie(
                    COOKIE,
                    new_token,
                    httponly=True,
                    samesite="lax",
                    secure=urlsplit(self.settings.origin).scheme == "https",
                    max_age=28800 if data.get("principal") else 600,
                    path="/",
                )
            else:
                response.delete_cookie(COOKIE, path="/")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; frame-src 'self'; object-src 'self'; "
            "base-uri 'none'; frame-ancestors 'self'; form-action 'self'"
        )
        return response


def principal(request: Request) -> str:
    from retrievec.app.main import APIError

    value = request.session.get("principal")
    if not value:
        raise APIError(401, "unauthenticated", "Sign in to continue")
    return value


def install_auth(app, sessions=None):
    settings = app.state.settings
    sessions = sessions or Sessions(app.state.registry)
    app.add_middleware(SessionMiddleware, sessions=sessions, settings=settings)
    oauth = OAuth()
    provider = oauth.register(
        "identity",
        client_id=settings.client_id,
        client_secret=settings.client_secret or None,
        server_metadata_url=settings.issuer.rstrip("/") + "/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid profile",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": "client_secret_basic"
            if settings.client_secret
            else "none",
            "timeout": 10,
        },
    )
    app.state.oidc = provider

    @app.get("/auth/login")
    async def login(request: Request):
        request.session.clear()
        request.state.rotate_session = True
        request.session["csrf"] = secrets.token_urlsafe(32)
        return await provider.authorize_redirect(
            request, settings.origin + "/auth/callback", prompt="select_account"
        )

    @app.get("/auth/callback")
    async def callback(request: Request):
        from retrievec.app.main import APIError

        # Consume the flow before contacting the provider, preventing concurrent replay.
        old = request.cookies.get(COOKIE, "")
        flow = await run_in_threadpool(sessions.consume, old)
        request.session.clear()
        request.session.update(flow)
        request.state.rotate_session = True
        try:
            state = request.query_params.get("state", "")
            state_data = await provider.framework.get_state_data(request.session, state)
            nonce = (state_data or {}).get("nonce")
            if not nonce:
                raise ValueError("missing login flow")
            token = await provider.authorize_access_token(
                request,
                claims_options={
                    "iss": {"essential": True, "value": settings.issuer},
                    "nonce": {"essential": True, "value": nonce},
                },
                leeway=30,
            )
            info = token.get("userinfo", {})
            if (
                not info.get("sub")
                or info.get("iss") != settings.issuer
                or info.get("nonce") != nonce
            ):
                raise ValueError("required identity claims missing")
            user = await run_in_threadpool(sessions.identity, settings.issuer, info["sub"])
        except Exception:
            request.session.clear()
            raise APIError(
                401, "login_failed", "Login could not be verified; start again"
            ) from None
        request.session.clear()
        request.session.update(principal=user, csrf=secrets.token_urlsafe(32))
        return RedirectResponse("/", status_code=303)

    @app.post("/auth/logout")
    async def logout(request: Request):
        request.session.clear()
        request.state.rotate_session = True
        return {"status": "signed_out"}

    @app.get("/api/v1/me")
    def me(request: Request):
        return {"principal_id": principal(request), "csrf_token": request.session["csrf"]}
