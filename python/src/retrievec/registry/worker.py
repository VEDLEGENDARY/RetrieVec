"""Local full-collection ingestion with immutable outputs and fenced activation."""

import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import grpc

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import canonical, digest, load_snapshot, parse_json
from retrievec.registry.artifacts import Store, prepare
from retrievec.registry.database import Conflict, Registry
from retrievec.registry.jobs import Jobs, LeaseLost
from retrievec.registry.scheduling import heavy_slot
from retrievec.telemetry import correlate, emit, request_identity


def publish_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    stage = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(stage, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != data:
                raise Conflict("immutable artifact conflict") from None
    finally:
        stage.unlink(missing_ok=True)


def stage_inputs(store: Store, manifest_path: Path, source_root: Path) -> dict:
    manifest = parse_json(manifest_path.read_bytes())
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("sources"), list)
    ):
        raise ValueError("invalid source manifest")
    source_root = source_root.resolve()
    for source in manifest["sources"]:
        path = (source_root / source["path"]).resolve()
        if (
            not path.is_relative_to(source_root)
            or not path.is_file()
            or path.stat().st_size > 64 * 1024 * 1024
        ):
            raise ValueError("source outside configured root or too large")
        raw = path.read_bytes()
        if digest(raw) != source["source_sha256"]:
            raise ValueError("source checksum mismatch")
        source["path"] = source["source_sha256"] + path.suffix.lower()
        publish_bytes(store.root / "sources" / source["path"], raw)
    raw = canonical(manifest)
    key = digest(raw)
    publish_bytes(store.root / "inputs" / (key + ".json"), raw)
    return {"manifest_hash": key}


class Worker:
    def __init__(self, registry: Registry, store: Store, principal: str, engine: Path, node):
        self.registry, self.store, self.principal = registry, store, principal
        self.engine, self.node = engine, node
        self.jobs = Jobs(registry, principal)

    def run_once(self) -> dict | None:
        with heavy_slot(self.registry, "ingestion") as acquired:
            return self.claim_once() if acquired else None

    def claim_once(self) -> dict | None:
        job = self.jobs.claim()
        if job is None:
            return None
        with correlate(
            request_id=request_identity(job.get("request_id")),
            job_id=job["job_id"],
            collection_id=job["collection_id"],
            service="ingestion",
        ):
            emit("worker.active", worker_kind="ingestion", active_workers=1)
            emit(
                "ingestion.claimed",
                attempt=job["attempts"],
                queue_age_ms=max(0, (datetime.now(UTC) - job["created_at"]).total_seconds() * 1000),
            )
            started = time.perf_counter()
            try:
                result = self.execute(job)
                emit(
                    "ingestion.finished",
                    outcome=result["state"],
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                    error_code=result.get("error_code"),
                )
                return result
            finally:
                emit("worker.idle", worker_kind="ingestion", active_workers=0)

    def execute(self, job):
        stop, lost = threading.Event(), threading.Event()

        def heartbeat():
            while not stop.wait(15):
                try:
                    self.jobs.heartbeat(job)
                except Exception:
                    lost.set()
                    return

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            payload = job["payload"]["input"]
            configuration = job["payload"]["configuration"]
            from retrievec.registry.artifacts import identity

            key = identity(payload["manifest_hash"], "")
            source_manifest = self.store.root / "inputs" / (key + ".json")
            if digest(source_manifest.read_bytes()) != key:
                raise ValueError("source manifest changed")
            self.jobs.checkpoint(job, "extract", {"manifest_hash": key})
            if configuration.get("private_upload") or configuration.get("extraction_adapter"):
                command = [
                    sys.executable,
                    "-m",
                    "retrievec.app.extract",
                    str(source_manifest),
                    str(self.store.root),
                    job["collection_id"],
                    str(self.engine),
                ]
                if configuration.get("evidence_bundles") or configuration.get("extraction_adapter"):
                    raw_config = canonical(
                        {
                            key: configuration[key]
                            for key in ("evidence_bundles", "extraction_adapter")
                            if key in configuration
                        }
                    )
                    if len(raw_config) > 65536:
                        raise ValueError("extraction configuration exceeds limit")
                    config_path = (
                        self.store.root / "extractor-configs" / (digest(raw_config) + ".json")
                    )
                    publish_bytes(config_path, raw_config)
                    command.append(str(config_path))
                options = (
                    {"creationflags": subprocess.CREATE_NO_WINDOW}
                    if os.name == "nt"
                    else {"start_new_session": True}
                )
                with subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, **options
                ) as process:
                    try:
                        output, _ = process.communicate(timeout=120)
                    except subprocess.TimeoutExpired:
                        from retrievec.extraction.adapters import terminate

                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            terminate(process)
                        raise
                    if process.returncode:
                        raise subprocess.CalledProcessError(
                            process.returncode, command, output=output
                        )
                corpus = self.store.path("corpora", output.strip(), "ss_")
            else:
                corpus = import_manifest(
                    source_manifest,
                    self.store.root / "sources",
                    self.store.root / "corpora",
                    job["collection_id"],
                    configuration.get("token_budget", 256),
                    GoAnalyzer(self.engine),
                    evidence_bundles=configuration.get("evidence_bundles"),
                    evidence_root=self.store.root,
                )
            self.jobs.checkpoint(job, "chunk", {"corpus_snapshot_id": corpus.name})
            embedding_id = None
            if configuration.get("embedding"):
                self.jobs.checkpoint(job, "embed", {"corpus_snapshot_id": corpus.name})
                from retrievec.dense.artifacts import build_embeddings
                from retrievec.dense.model import adapter

                embedding_id = build_embeddings(
                    self.store, corpus, adapter(configuration["embedding"])
                )
            self.jobs.checkpoint(job, "sparse_build", {"corpus_snapshot_id": corpus.name})
            snapshot_id = self.store.build(self.engine, corpus, embedding_id)
            self.jobs.checkpoint(job, "validate", {"snapshot_id": snapshot_id})
            prepare(self.registry, self.store, self.principal, snapshot_id, self.node)
            self.jobs.checkpoint(job, "activate", {"snapshot_id": snapshot_id})
            if lost.is_set():
                raise LeaseLost("heartbeat failed")
            _, papers, _ = load_snapshot(corpus)
            self.jobs.complete(job, snapshot_id, papers=papers)
            return {"job_id": str(job["job_id"]), "state": "succeeded", "snapshot_id": snapshot_id}
        except LeaseLost:
            return {"job_id": str(job["job_id"]), "state": "lease_lost"}
        except Exception as error:
            transient = isinstance(error, (grpc.RpcError, OSError))
            code = (
                "unavailable"
                if transient
                else "stale_parent"
                if isinstance(error, Conflict)
                else "invalid_input"
            )
            if isinstance(error, subprocess.TimeoutExpired):
                code = "extraction_timeout"
            elif isinstance(error, subprocess.CalledProcessError):
                safe_code = (error.stdout or "").strip()
                if safe_code in ("encrypted_pdf", "ocr_required", "invalid_input"):
                    code = safe_code
            try:
                self.jobs.fail(job, code, retry=transient)
            except (LeaseLost, PermissionError):
                return {"job_id": str(job["job_id"]), "state": "cancelled"}
            return {
                "job_id": str(job["job_id"]),
                "state": "retry_wait"
                if transient and job["attempts"] < job["max_attempts"]
                else "failed",
                "error_code": code,
            }
        finally:
            stop.set()
            thread.join(timeout=10)
