"""Deterministic OpenAPI export; no database, model or identity server needed."""

import argparse
import json
from pathlib import Path

from retrievec.app.config import Settings
from retrievec.app.main import create_app


def specification():
    app = create_app(
        Settings(
            dsn="unused", origin="https://workspace.example", issuer="https://identity.example"
        )
    )
    document = app.openapi()
    document["servers"] = [{"url": "/"}]
    document["components"].setdefault("securitySchemes", {})["browserSession"] = {
        "type": "apiKey",
        "in": "cookie",
        "name": "retrievec_session",
        "description": "Opaque PostgreSQL-backed session established by the OIDC flow.",
    }
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            if path.startswith("/api/v1/"):
                operation["security"] = [{"browserSession": []}]
            if method in {"post", "put", "patch", "delete"}:
                operation.setdefault("parameters", []).extend(
                    [
                        {
                            "name": "X-CSRF-Token",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Session-bound CSRF token.",
                        },
                        {
                            "name": "Origin",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Configured application origin.",
                        },
                    ]
                )
            if path.endswith("/events"):
                operation["x-retrievec-streaming"] = {
                    "transport": "text/event-stream",
                    "finite_batch": True,
                    "mock_limit": "JSON mocks do not verify replay, cancellation or authorization.",
                }
    return document


def encoded():
    return (json.dumps(specification(), indent=2, sort_keys=True) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("contracts/openapi.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = encoded()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != data:
            parser.exit(1, "OpenAPI drift: regenerate and review contracts/openapi.json\n")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)


if __name__ == "__main__":
    main()
