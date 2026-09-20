"""One bounded generation consumer, independent of the HTTP process."""

import asyncio
import hashlib
import re
import threading
import time
import uuid

import grpc
import httpx

from retrievec.app.answers import abstention, answer_schema, validate_answer
from retrievec.app.config import Settings
from retrievec.app.generation import (
    LlamaProvider,
    ProviderError,
    cancellable,
    load_providers,
    pack_evidence,
)
from retrievec.app.run_state import RunState
from retrievec.client.rpc import RPCClient
from retrievec.corpus.snapshot import load_snapshot
from retrievec.dense.hybrid import PinnedClient
from retrievec.dense.model import adapter
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry


class ResearchWorker:
    def __init__(self, registry, settings, *, providers=None, provider_factory=LlamaProvider):
        self.registry, self.settings = registry, settings
        self.state = RunState(registry)
        self.providers = (
            providers if providers is not None else load_providers(settings.generation_config)
        )
        self.provider_factory = provider_factory
        self.encoder = None

    def retrieve(self, run):
        config = run["configuration"]
        store = Store(self.settings.store)
        if config["retrieval"] != "sparse" and self.encoder is None:
            self.encoder = adapter(self.settings.embedding)
        node = RPCClient(
            self.settings.rpc_address, self.settings.read_token, principal=run["owner_id"]
        )
        try:
            client = PinnedClient(
                self.registry,
                store,
                node,
                run["owner_id"],
                run["collection_id"],
                config["retrieval"],
                self.encoder,
                run["snapshot_id"],
                config["candidates"],
            )
            result = client.search(run["effective_query"], top_k=config["top_k"])
            _, papers, _ = load_snapshot(
                store.path("corpora", client.manifest["corpus_snapshot_id"], "ss_")
            )
            metadata = {paper["paper_version_id"]: paper for paper in papers}
            with self.registry.connect() as db:
                self.state.access(db, run)
                rows = db.execute(
                    "SELECT * FROM upload_sources WHERE collection_id=%s", (run["collection_id"],)
                ).fetchall()
            sources = {(row["paper_id"], row["source_hash"]): row for row in rows}
            for hit in result["hits"]:
                paper = metadata[hit["paper_version_id"]]
                source = sources.get((paper["paper_id"], paper["source_sha256"]))
                hit["authors"] = paper["authors"]
                hit["source_sha256"] = paper["source_sha256"]
                hit["source_id"] = str(source["source_id"]) if source else None
            return result
        finally:
            node.close()

    def verify_sources(self, run, evidence):
        registered = self.registry.resolve(
            run["owner_id"], run["collection_id"], run["snapshot_id"]
        )
        store = Store(self.settings.store)
        _, _, chunks = load_snapshot(store.path("corpora", registered["corpus_snapshot_id"], "ss_"))
        retained = {chunk["chunk_id"]: chunk for chunk in chunks}
        with self.registry.connect() as db:
            self.state.access(db, run)
            for item in evidence:
                chunk = retained.get(item["chunk_id"])
                if not chunk or chunk["text"] != item["text"]:
                    raise ProviderError("retained evidence unavailable")
                if item["source_id"] is None:
                    # Curated snapshots can retain exact passages without an uploaded original.
                    item["original_available"] = False
                    continue
                source = self.state.policy.owned(db, run["owner_id"], "source", item["source_id"])
                if (
                    source["collection_id"] != run["collection_id"]
                    or source["source_hash"] != item["source_sha256"]
                    or not re.fullmatch(r"[0-9a-f]{32}\.(pdf|txt|md)", source["storage_key"])
                ):
                    raise ProviderError("source provenance mismatch")
                root = (self.settings.store / "sources").resolve()
                path = root / source["storage_key"]
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ProviderError("source unavailable")
                with path.open("rb") as file:
                    if (
                        path.stat().st_size != source["size_bytes"]
                        or hashlib.file_digest(file, "sha256").hexdigest() != source["source_hash"]
                    ):
                        raise ProviderError("source integrity mismatch")
                item["original_available"] = True

    def run_once(self):
        run = self.state.claim()
        if run is None:
            return False
        cancelled, done = threading.Event(), threading.Event()

        def heartbeat():
            while not done.wait(2):
                try:
                    if not self.state.heartbeat(run):
                        cancelled.set()
                        return
                except Exception:
                    cancelled.set()
                    return

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        started = time.perf_counter()
        error = "provider_unavailable"
        try:
            if not self.state.heartbeat(run):
                return True
            configured = self.providers.get(run["configuration"]["provider"])
            if configured is None or configured.identity != run["configuration"]["provider_hash"]:
                raise ProviderError("provider configuration changed")
            error = "retrieval_unavailable"
            retrieved = self.retrieve(run)
            if not self.state.transition(run, "generating"):
                return True
            provider = self.provider_factory(configured)
            error = "provider_failed"

            async def generate():
                if not retrieved["hits"]:
                    return {
                        "evidence": [],
                        "excluded": [],
                        "truncated": [],
                        "input_tokens": 0,
                        "reserved_output_tokens": configured.output_tokens,
                    }, None
                packet = await pack_evidence(provider, run["effective_query"], retrieved["hits"])
                if not packet["evidence"]:
                    return packet, None
                raw = await provider.generate(packet["prompt"], answer_schema(packet["evidence"]))
                return packet, raw

            packet, raw = asyncio.run(
                cancellable(asyncio.wait_for(generate(), timeout=240), cancelled)
            )
            if not self.state.transition(run, "validating"):
                return True
            error = "invalid_answer"
            answer = validate_answer(raw, packet["evidence"]) if raw is not None else abstention()
            error = "source_unavailable"
            self.verify_sources(run, packet["evidence"])
            evidence = [
                {**item, "citation_id": str(uuid.uuid5(run["run_id"], item["evidence_id"]))}
                for item in packet["evidence"]
            ]
            result = {
                "schema_version": 1,
                "answer": answer,
                "evidence": evidence,
                "budget": {k: v for k, v in packet.items() if k not in ("evidence", "prompt")},
                "retrieval": retrieved["configuration"],
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "validation": "structural_only",
                "human_review": "pending",
            }
            self.state.transition(run, "completed", result=result, evidence=evidence)
        except (asyncio.CancelledError, PermissionError):
            # Revocation/cancellation fences publication; expired work is failed by the next claim.
            pass
        except (ValueError, OSError, httpx.HTTPError, grpc.RpcError):
            try:
                self.state.transition(run, "failed", code=error)
            except PermissionError:
                pass
        finally:
            done.set()
            thread.join(timeout=6)
        return True


def main():
    settings = Settings.from_env()
    registry = Registry(settings.dsn)
    worker = ResearchWorker(registry, settings)
    with registry.connect() as guard:
        if not guard.execute("SELECT pg_try_advisory_lock(7823403) AS acquired").fetchone()[
            "acquired"
        ]:
            raise SystemExit("A research worker is already running")
        guard.commit()
        while True:
            if not worker.run_once():
                time.sleep(1)


if __name__ == "__main__":
    main()
