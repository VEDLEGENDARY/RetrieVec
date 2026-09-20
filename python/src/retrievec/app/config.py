import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    dsn: str
    origin: str = "http://127.0.0.1:8000"
    issuer: str = "http://127.0.0.1:8080/realms/retrievec"
    client_id: str = "retrievec"
    client_secret: str = ""
    local_http: bool = False
    store: Path = Path("artifacts/store")
    rpc_address: str = "127.0.0.1:8092"
    read_token: str = ""
    embedding: str = "minilm"
    max_file_bytes: int = 25 * 1024 * 1024
    max_files: int = 10
    storage_quota: int = 250 * 1024 * 1024
    max_pending_jobs: int = 3
    generation_config: Path | None = None

    def __post_init__(self):
        for address in (self.origin, self.issuer):
            url = urlsplit(address)
            if not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("invalid application URL")
            if url.scheme != "https" and not (
                self.local_http
                and url.scheme == "http"
                and url.hostname in ("localhost", "127.0.0.1", "::1")
            ):
                raise ValueError("HTTP requires explicit localhost development mode")
        if urlsplit(self.origin).path not in ("", "/"):
            raise ValueError("application origin must not include a path")
        if self.origin.endswith("/"):
            raise ValueError("application origin must not have a trailing slash")
        if (
            not 1 <= self.max_files <= 10
            or not 1 <= self.max_file_bytes <= 25 * 1024 * 1024
            or self.storage_quota < self.max_file_bytes
            or not 1 <= self.max_pending_jobs <= 10
        ):
            raise ValueError("invalid upload limits")

    @classmethod
    def from_env(cls):
        return cls(
            dsn=os.environ["RETRIEVEC_DSN"],
            origin=os.getenv("RETRIEVEC_ORIGIN", "http://127.0.0.1:8000"),
            issuer=os.getenv("RETRIEVEC_OIDC_ISSUER", "http://127.0.0.1:8080/realms/retrievec"),
            client_id=os.getenv("RETRIEVEC_OIDC_CLIENT", "retrievec"),
            client_secret=os.getenv("RETRIEVEC_OIDC_SECRET", ""),
            local_http=os.getenv("RETRIEVEC_LOCAL_HTTP") == "1",
            store=Path(os.getenv("RETRIEVEC_STORE", "artifacts/store")),
            rpc_address=os.getenv("RETRIEVEC_RPC", "127.0.0.1:8092"),
            read_token=os.getenv("RETRIEVEC_READ_TOKEN", ""),
            embedding=os.getenv("RETRIEVEC_EMBEDDING", "minilm"),
            generation_config=(
                Path(os.environ["RETRIEVEC_GENERATION_CONFIG"])
                if os.getenv("RETRIEVEC_GENERATION_CONFIG")
                else None
            ),
        )
