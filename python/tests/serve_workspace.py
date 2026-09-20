"""Test-only OIDC issuer and real workspace services for browser integration.

Requires an isolated PostgreSQL test DSN. Never imported by the application.
"""

import base64
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import psycopg
import uvicorn
from joserfc import jwt
from joserfc.jwk import RSAKey
from psycopg import sql
from psycopg.conninfo import make_conninfo
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.client.rpc import RPCClient
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry
from retrievec.registry.worker import Worker

ISSUER = "http://127.0.0.1:8101"
ORIGIN = "http://127.0.0.1:8000"
KEY = RSAKey.generate_key(2048, parameters={"kid": "browser-test"})
CODES = {}


class IdentityHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/.well-known/openid-configuration":
            return self.reply(
                {
                    "issuer": ISSUER,
                    "authorization_endpoint": ISSUER + "/authorize",
                    "token_endpoint": ISSUER + "/token",
                    "jwks_uri": ISSUER + "/keys",
                    "id_token_signing_alg_values_supported": ["RS256"],
                }
            )
        if url.path == "/keys":
            return self.reply({"keys": [KEY.as_dict(private=False)]})
        if url.path != "/authorize":
            return self.reply({}, 404)
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        if (
            params.get("redirect_uri") != ORIGIN + "/auth/callback"
            or params.get("code_challenge_method") != "S256"
        ):
            return self.reply({}, 400)
        if "user" not in params:
            import html

            content = (
                '<!doctype html><html lang="en"><title>Test identity</title>'
                "<h1>Test identity provider</h1>"
            )
            for user in ("a", "b"):
                href = html.escape(urlencode(params | {"user": user}))
                content += f'<a href="/authorize?{href}">Sign in as {user}</a><br>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode())
            return
        code = secrets.token_urlsafe(24)
        CODES[code] = params
        self.send_response(302)
        self.send_header(
            "Location",
            ORIGIN + "/auth/callback?" + urlencode({"code": code, "state": params["state"]}),
        )
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 8192))
        values = {k: v[0] for k, v in parse_qs(body.decode()).items()}
        params = CODES.pop(values.get("code"), {})
        verifier = values.get("code_verifier", "")
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        if not params or challenge != params["code_challenge"]:
            return self.reply({"error": "invalid_grant"}, 400)
        token = jwt.encode(
            {"alg": "RS256", "kid": "browser-test"},
            {
                "iss": ISSUER,
                "aud": "retrievec",
                "sub": params["user"],
                "nonce": params["nonce"],
                "iat": int(time.time()),
                "exp": int(time.time()) + 120,
            },
            KEY,
        )
        self.reply({"id_token": token, "access_token": "test-only", "token_type": "Bearer"})


def main():
    dsn = os.environ["RETRIEVEC_TEST_DSN"]
    schema = "browser_" + uuid.uuid4().hex
    with psycopg.connect(dsn) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped_dsn = make_conninfo(dsn, options="-c search_path=" + schema)
    registry = Registry(scoped_dsn)
    registry.migrate()
    directory = tempfile.TemporaryDirectory()
    store = Store(Path(directory.name))
    token, worker_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    engine = Path(os.environ["RETRIEVEC_ENGINE"]).resolve()
    process = subprocess.Popen(
        [str(engine), "rpc", "--store", str(store.root), "--listen", "127.0.0.1:8092"],
        env={
            **os.environ,
            "RETRIEVEC_DSN": scoped_dsn,
            "RETRIEVEC_PRINCIPAL": "*",
            "RETRIEVEC_READ_TOKEN": token,
            "RETRIEVEC_WORKER_TOKEN": worker_token,
        },
    )
    identity = ThreadingHTTPServer(("127.0.0.1", 8101), IdentityHandler)
    threading.Thread(target=identity.serve_forever, daemon=True).start()
    stop = threading.Event()

    def work():
        while not stop.wait(0.25):
            with registry.connect() as db:
                owners = db.execute(
                    "SELECT DISTINCT owner_id FROM collections WHERE NOT archived"
                ).fetchall()
            for row in owners:
                node = RPCClient("127.0.0.1:8092", worker_token, principal=row["owner_id"])
                try:
                    Worker(registry, store, row["owner_id"], engine, node).run_once()
                finally:
                    node.close()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    try:
        app = create_app(
            Settings(
                dsn=scoped_dsn,
                local_http=True,
                issuer=ISSUER,
                store=store.root,
                read_token=token,
                embedding="fixture",
            )
        )
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    finally:
        stop.set()
        thread.join(timeout=130)
        process.terminate()
        process.wait(timeout=10)
        identity.shutdown()
        with psycopg.connect(dsn) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        directory.cleanup()


if __name__ == "__main__":
    main()
