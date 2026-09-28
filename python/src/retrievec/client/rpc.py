"""Generated RPC client with bounded deadlines and explicit snapshot identities."""

import math
import os
import time
from pathlib import Path

import grpc

from retrievec.observability import carrier, span
from retrievec.retrieval.v1 import retrieval_pb2 as pb
from retrievec.retrieval.v1 import retrieval_pb2_grpc as rpc
from retrievec.telemetry import CONTEXT, emit, request_identity


class RPCClient:
    def __init__(
        self, address: str, token: str, timeout: float = 5, *, principal: str | None = None
    ):
        if not token or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("credential and finite deadline required")
        if principal is not None and (
            not principal
            or len(principal) > 256
            or not principal.isascii()
            or any(ord(character) < 32 or ord(character) == 127 for character in principal)
        ):
            raise ValueError("invalid principal assertion")
        host = address.rsplit(":", 1)[0].strip("[]")
        import ipaddress

        options = [
            ("grpc.max_receive_message_length", 4 << 20),
            ("grpc.max_send_message_length", 4 << 20),
        ]
        paths = [os.getenv("RETRIEVEC_RPC_TLS_" + name) for name in ("CA", "CERT", "KEY")]
        if any(paths):
            if not all(paths):
                raise ValueError("RPC CA, client certificate and key must all be configured")
            ca, cert, key = [Path(path).read_bytes() for path in paths]
            credentials = grpc.ssl_channel_credentials(ca, key, cert)
            self.channel = grpc.secure_channel(address, credentials, options=options)
        else:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("unencrypted RPC is restricted to loopback")
            self.channel = grpc.insecure_channel(address, options=options)
        self.stub = rpc.RetrievalStub(self.channel)
        self.metadata = (("authorization", "Bearer " + token),)
        if principal is not None:
            if not principal or len(principal) > 256 or not principal.isascii():
                raise ValueError("invalid principal assertion")
            self.metadata += (("x-retrievec-principal", principal),)
        self.timeout = timeout

    def close(self):
        self.channel.close()

    def ready(self):
        from grpc_health.v1 import health_pb2, health_pb2_grpc

        response = health_pb2_grpc.HealthStub(self.channel).Check(
            health_pb2.HealthCheckRequest(service="ready"),
            timeout=self.timeout,
            metadata=self.metadata + tuple(carrier().items()),
        )
        return response.status == health_pb2.HealthCheckResponse.SERVING

    def call(self, method, request):
        with span("rpc.retrieval"):
            return self._call(method, request)

    def _call(self, method, request):
        deadline = time.monotonic() + self.timeout
        started = time.perf_counter()
        trace = CONTEXT.get()
        metadata = self.metadata + (("x-request-id", request_identity(trace.get("request_id"))),)
        metadata += tuple(carrier().items())
        for key in ("job_id", "run_id"):
            if trace.get(key):
                metadata += (("x-retrievec-" + key.replace("_", "-"), str(trace[key])),)
        for attempt in range(2):
            try:
                value = method(
                    request, timeout=max(0, deadline - time.monotonic()), metadata=metadata
                )
                emit(
                    "rpc.finished",
                    service="rpc_client",
                    outcome="completed",
                    attempt=attempt + 1,
                    snapshot_id=request.snapshot_id,
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
                return value
            except grpc.RpcError as error:
                emit(
                    "rpc.attempt",
                    service="rpc_client",
                    outcome="failed",
                    attempt=attempt + 1,
                    error_code=error.code().name,
                    snapshot_id=request.snapshot_id,
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
                if (
                    attempt
                    or error.code() != grpc.StatusCode.UNAVAILABLE
                    or time.monotonic() >= deadline
                ):
                    raise

    def prepare(self, collection: str, snapshot_id: str):
        return self.call(
            self.stub.PrepareSnapshot,
            pb.SnapshotRequest(collection_id=collection, snapshot_id=snapshot_id),
        )

    def info(self, collection: str, snapshot_id: str):
        return self.call(
            self.stub.GetSnapshotInfo,
            pb.SnapshotRequest(collection_id=collection, snapshot_id=snapshot_id),
        )

    def search(
        self,
        collection: str,
        snapshot_id: str,
        query: str,
        mode: str = "free_text",
        limit: int = 100,
        explain: bool = False,
    ):
        if (
            mode not in ("free_text", "structured")
            or type(limit) is not int
            or not 1 <= limit <= 1000
            or not isinstance(query, str)
            or not 1 <= len(query) <= 4096
        ):
            raise ValueError("invalid query, mode or candidate limit")
        value = self.call(
            self.stub.Search,
            pb.SearchRequest(
                collection_id=collection,
                snapshot_id=snapshot_id,
                query=query,
                mode=pb.FREE_TEXT if mode == "free_text" else pb.STRUCTURED,
                candidate_limit=limit,
                explain=explain,
            ),
        )
        if value.snapshot_id != snapshot_id or any(
            not math.isfinite(hit.score) for hit in value.hits
        ):
            raise ValueError("invalid RPC result identity or score")
        return value
