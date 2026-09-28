from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from retrievec.app.config import Settings
from retrievec.app.errors import APIError
from retrievec.app.schemas import Error
from retrievec.registry.database import Conflict, Registry


def create_app(settings: Settings | None = None, *, registry=None, sessions=None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="RetrieVec workspace",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        responses={status: {"model": Error} for status in (401, 403, 404, 409, 422, 429, 503)},
    )
    app.state.settings = settings
    app.state.registry = registry or Registry(settings.dsn)
    from retrievec.app.auth import install_auth

    install_auth(app, sessions)
    from retrievec.app.resources import install_resources

    install_resources(app)
    from retrievec.app.uploads import install_uploads

    install_uploads(app)
    from retrievec.app.search import install_search

    install_search(app)
    from retrievec.app.research import install_research

    install_research(app)
    from retrievec.app.exports import install_exports

    install_exports(app)
    from retrievec.app.evidence import install_evidence

    install_evidence(app)
    from retrievec.app.telemetry import RequestTelemetry

    app.add_middleware(RequestTelemetry)

    @app.exception_handler(APIError)
    async def api_error(request: Request, error: APIError):
        return JSONResponse(
            {"code": error.code, "message": error.message},
            status_code=error.status,
            headers={"Retry-After": "2"} if error.status in (429, 503) else None,
        )

    @app.exception_handler(PermissionError)
    async def unavailable(request: Request, error: PermissionError):
        return JSONResponse(
            {"code": "not_found", "message": "Resource unavailable"}, status_code=404
        )

    @app.exception_handler(Conflict)
    async def conflict(request: Request, error: Conflict):
        return JSONResponse(
            {"code": "conflict", "message": "Resource state changed"}, status_code=409
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError):
        return JSONResponse(
            {"code": "invalid_input", "message": "Invalid request fields or mode"}, status_code=422
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return JSONResponse(
            {"code": "request_error", "message": "Request could not be accepted"},
            status_code=error.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception):
        return JSONResponse(
            {"code": "service_unavailable", "message": "Service unavailable; try again shortly"},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def ready():
        import grpc
        import psycopg

        from retrievec.client.rpc import RPCClient

        try:
            with psycopg.connect(settings.dsn, connect_timeout=2) as db:
                db.execute("SET LOCAL statement_timeout = '1500ms'")
                db.execute("SELECT 1 FROM collections LIMIT 0")
            node = RPCClient(settings.rpc_address, settings.read_token, timeout=1)
            try:
                if not node.ready():
                    return JSONResponse({"status": "unavailable"}, status_code=503)
            finally:
                node.close()
        except (psycopg.Error, grpc.RpcError, OSError, ValueError):
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ready"}

    from pathlib import Path

    from starlette.staticfiles import StaticFiles

    frontend = settings.frontend or Path(__file__).resolve().parents[4] / "web" / "dist"
    if settings.frontend is not None and not (frontend / "index.html").is_file():
        raise ValueError("configured frontend must contain index.html")
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="workspace")

    return app


def main():
    import os

    import uvicorn

    from retrievec.telemetry import configure

    configure("retrievec.api")

    uvicorn.run(
        create_app(),
        host=os.getenv("RETRIEVEC_HOST", "127.0.0.1"),
        port=int(os.getenv("RETRIEVEC_PORT", "8000")),
        proxy_headers=False,
        limit_concurrency=32,
        timeout_keep_alive=5,
        access_log=False,
    )


if __name__ == "__main__":
    main()
