"""Bounded client for the local sparse retrieval service."""

import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_RESPONSE = 16 * 1024 * 1024


class RetrievalError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


def finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:8091", timeout: float = 10):
        parsed = urlparse(base_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid service URL")
        if not finite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        request = Request(
            self.base_url + path, data=data, headers={"Content-Type": "application/json"}
        )
        status = 200
        try:
            try:
                response = urlopen(request, timeout=self.timeout)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise RetrievalError("invalid_response", "response too large", status)
            value = json.loads(raw)
        except (URLError, TimeoutError, OSError) as error:
            raise RetrievalError("transport_error", str(error)) from error
        except (UnicodeError, ValueError) as error:
            raise RetrievalError("invalid_response", "invalid JSON response", status) from error
        if not isinstance(value, dict):
            raise RetrievalError("invalid_response", "expected response object", status)
        if status != 200:
            raise RetrievalError(
                str(value.get("code", "http_error")),
                str(value.get("message", "request failed")),
                status,
            )
        return value

    def stats(self) -> dict:
        value = self._request("/v1/stats")
        for key in ("snapshot_id", "collection_id", "analyzer_version", "scoring_version"):
            if not isinstance(value.get(key), str) or not value[key]:
                raise RetrievalError("invalid_response", f"missing {key}")
        if not isinstance(value.get("configuration"), dict) or not isinstance(
            value.get("statistics"), dict
        ):
            raise RetrievalError("invalid_response", "missing configuration or statistics")
        return value

    def search(
        self, query: str, mode: str = "free_text", top_k: int = 10, explain: bool = False
    ) -> dict:
        value = self._request(
            "/v1/search", {"query": query, "mode": mode, "top_k": top_k, "explain": explain}
        )
        for key in (
            "request_id",
            "snapshot_id",
            "collection_id",
            "analyzer_version",
            "scoring_version",
        ):
            if not isinstance(value.get(key), str) or not value[key]:
                raise RetrievalError("invalid_response", f"missing {key}")
        hits = value.get("hits")
        total = value.get("total_matches")
        if (
            not isinstance(hits, list)
            or type(total) is not int
            or total < len(hits)
            or len(hits) > top_k
        ):
            raise RetrievalError("invalid_response", "invalid hit count")
        if (
            not isinstance(value.get("configuration"), dict)
            or not isinstance(value.get("timings"), dict)
            or not finite(value["timings"].get("search_ms"))
        ):
            raise RetrievalError("invalid_response", "missing configuration or timing")
        seen = set()
        previous = None
        for rank, hit in enumerate(hits, 1):
            if (
                not isinstance(hit, dict)
                or hit.get("rank") != rank
                or not finite(hit.get("score"))
                or hit["score"] < 0
            ):
                raise RetrievalError("invalid_response", "invalid rank or score")
            for key in ("chunk_id", "paper_id", "paper_version_id", "title", "text"):
                if not isinstance(hit.get(key), str) or not hit[key]:
                    raise RetrievalError("invalid_response", f"invalid hit {key}")
            order = (-hit["score"], hit["chunk_id"])
            if hit["chunk_id"] in seen or (previous is not None and order < previous):
                raise RetrievalError("invalid_response", "duplicate or unsorted hits")
            pages = hit.get("page_range", "missing")
            if pages is not None and (
                not isinstance(pages, list)
                or len(pages) != 2
                or any(type(page) is not int for page in pages)
                or not 1 <= pages[0] <= pages[1]
            ):
                raise RetrievalError("invalid_response", "invalid page range")
            seen.add(hit["chunk_id"])
            previous = order
        return value
