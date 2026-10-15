import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from retrievec.app.auth import COOKIE, Sessions
from retrievec.app.config import Settings
from retrievec.app.main import create_app
from retrievec.registry.database import Registry


@unittest.skipUnless(os.getenv("RETRIEVEC_TEST_DSN"), "requires isolated PostgreSQL 18")
class WorkspaceDatabaseTests(unittest.TestCase):
    def setUp(self):
        root_dsn = os.environ["RETRIEVEC_TEST_DSN"]
        schema = "workspace_" + uuid.uuid4().hex
        with psycopg.connect(root_dsn) as db:
            db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

        def cleanup_schema():
            with psycopg.connect(root_dsn) as db:
                db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))

        self.addCleanup(cleanup_schema)
        self.registry = Registry(make_conninfo(root_dsn, options="-c search_path=" + schema))
        self.registry.migrate()
        self.sessions = Sessions(self.registry)
        suffix = uuid.uuid4().hex
        self.a = self.sessions.identity("test-issuer", "a" + suffix)
        self.b = self.sessions.identity("test-issuer", "b" + suffix)
        self.sessions.save("", "a" + suffix, {"principal": self.a, "csrf": "csrf"})
        self.sessions.save("", "b" + suffix, {"principal": self.b, "csrf": "csrf"})
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app(
            Settings(
                dsn=self.registry.dsn,
                local_http=True,
                store=Path(self.directory.name),
                embedding="fixture",
            )
        )
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8000")
        self.tokens = {self.a: "a" + suffix, self.b: "b" + suffix}
        self.headers = {"Origin": "http://127.0.0.1:8000", "X-CSRF-Token": "csrf"}

    def user(self, user):
        self.client.cookies.clear()
        self.client.cookies.set(COOKIE, self.tokens[user])

    def test_paper_library_upload_pagination_literal_filter_and_live_scope(self):
        self.user(self.a)
        collection = self.client.post(
            "/api/v1/collections", json={"title": "Paper library"}, headers=self.headers
        ).json()["collection_id"]
        route = f"/api/v1/collections/{collection}/papers"
        response = self.client.post(
            f"/api/v1/collections/{collection}/uploads",
            files=[
                ("files", ("method_100%.txt", b"Methods from a research paper")),
                ("files", ("findings.txt", b"Findings from a research paper")),
            ],
            headers=self.headers | {"Idempotency-Key": "library-test"},
        )
        self.assertEqual(response.status_code, 202, response.text)
        first = self.client.get(route, params={"limit": 1}).json()
        second = self.client.get(route, params={"limit": 1, "after": first["next_cursor"]}).json()
        self.assertIsNotNone(first["next_cursor"])
        self.assertIsNone(second["next_cursor"])
        self.assertNotEqual(first["items"][0]["source_id"], second["items"][0]["source_id"])
        self.assertEqual(first["items"][0]["state"], "queued")
        self.assertNotIn("storage_key", first["items"][0])
        for query in ("%", "_", "METHOD"):
            filtered = self.client.get(route, params={"q": query}).json()
            self.assertEqual(len(filtered["items"]), 1)
            self.assertEqual(filtered["items"][0]["display_name"], "method_100%.txt")
        self.user(self.b)
        self.assertEqual(self.client.get(route).status_code, 404)
        with self.registry.connect() as db:
            db.execute(
                "UPDATE collections SET visibility='curated' WHERE collection_id=%s", (collection,)
            )
        self.assertEqual(len(self.client.get(route).json()["items"]), 2)
        self.user(self.a)
        self.client.delete(f"/api/v1/collections/{collection}", headers=self.headers)
        for user in (self.a, self.b):
            self.user(user)
            self.assertEqual(self.client.get(route).status_code, 404)

    def test_pdf_page_images_require_live_snapshot_scope_and_match_retained_hash(self):
        from retrievec.corpus.importer import import_manifest
        from retrievec.corpus.pdf_locations import LocationIndex
        from retrievec.corpus.snapshot import canonical, digest, load_snapshot
        from test_importer import pdf_bytes

        root = self.app.state.settings.store
        source = pdf_bytes(["Retained passage"])
        (root / "paper.pdf").write_bytes(source)
        manifest_path = root / "input.json"
        manifest_path.write_bytes(
            canonical(
                {
                    "schema_version": 1,
                    "sources": [
                        {
                            "paper_id": "paper",
                            "title": "Title",
                            "authors": [],
                            "path": "paper.pdf",
                            "source_sha256": digest(source),
                            "source_url": None,
                            "license_note": "Fixture",
                        }
                    ],
                }
            )
        )
        collection = "pdf-images"
        self.registry.create_collection(self.a, collection)
        corpus_path = import_manifest(manifest_path, root, root / "corpora", collection)
        corpus, papers, chunks = load_snapshot(corpus_path)
        # Image resolution needs only a registered ready corpus; no RPC request participates.
        snapshot = self.registry.register(
            self.a,
            {
                "schema_version": 1,
                "collection_id": collection,
                "corpus_snapshot_id": corpus_path.name,
                "capabilities": ["sparse"],
            },
        )
        self.registry.ready(self.a, collection, snapshot)
        self.registry.activate(self.a, collection, snapshot, None)
        route = (
            f"/api/v1/collections/{collection}/snapshots/{snapshot}"
            f"/evidence/{chunks[0]['chunk_id']}/pdf-page"
        )
        self.user(self.b)
        self.assertEqual(self.client.get(route).status_code, 404)
        self.user(self.a)
        response = self.client.get(route)
        self.assertEqual(response.status_code, 200, response.text)
        locator = LocationIndex(root, corpus).attributes(chunks[0], papers[0])["pdf_locator"]
        self.assertEqual(digest(response.content), locator["image_sha256"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        image = root / "pdf-pages" / (locator["image_sha256"] + ".png")
        image.write_bytes(b"altered image")
        self.assertEqual(self.client.get(route).status_code, 409)
        self.client.delete("/api/v1/collections/" + collection, headers=self.headers)
        self.assertEqual(self.client.get(route).status_code, 404)

    def test_private_curated_and_archive_policy(self):
        self.user(self.a)
        response = self.client.post(
            "/api/v1/collections", json={"title": "Private"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 201, response.text)
        collection = response.json()["collection_id"]
        self.user(self.b)
        ids = [r["collection_id"] for r in self.client.get("/api/v1/collections").json()]
        self.assertNotIn(collection, ids)
        self.assertEqual(
            self.client.patch(
                "/api/v1/collections/" + collection, json={"title": "stolen"}, headers=self.headers
            ).status_code,
            404,
        )
        with self.registry.connect() as db:
            db.execute(
                "UPDATE collections SET visibility='curated' WHERE collection_id=%s", (collection,)
            )
        visible = self.client.get("/api/v1/collections").json()
        self.assertFalse(next(r for r in visible if r["collection_id"] == collection)["can_manage"])
        self.assertEqual(
            self.client.delete(
                "/api/v1/collections/" + collection, headers=self.headers
            ).status_code,
            404,
        )
        self.user(self.a)
        self.assertEqual(
            self.client.delete(
                "/api/v1/collections/" + collection, headers=self.headers
            ).status_code,
            204,
        )
        with self.registry.connect() as db, self.assertRaises(PermissionError):
            self.registry.authorize(db, self.a, collection)
        restore_url = f"/api/v1/collections/{collection}/restore"
        self.user(self.b)
        self.assertEqual(self.client.post(restore_url, headers=self.headers).status_code, 404)
        self.user(self.a)
        for _ in range(2):
            restored = self.client.post(restore_url, headers=self.headers)
            self.assertEqual(restored.status_code, 200, restored.text)
            self.assertTrue(restored.json()["can_manage"])
        with self.registry.connect() as db:
            self.registry.authorize(db, self.a, collection)

    def test_session_expiry_and_no_resurrection(self):
        token = self.tokens[self.a]
        self.sessions.save(token, "", {})
        self.sessions.save(token, token, {"principal": self.a})
        self.assertEqual(self.sessions.load(token), {})
        self.assertEqual(self.sessions.identity("test-issuer", "a" + token[1:]), self.a)

    def test_cached_history_and_reconnect_recheck_revoked_collection(self):
        from psycopg.types.json import Jsonb
        from retrievec.app.run_state import event

        # This scenario exercises live policy; source integrity has separate integration fixtures.
        source_check = patch("retrievec.app.research_worker.ResearchWorker.verify_sources")
        verify_sources = source_check.start()
        self.addCleanup(source_check.stop)
        self.registry.create_collection(self.a, "revocation-fixture")
        snapshot = self.registry.register(
            self.a,
            {
                "schema_version": 1,
                "collection_id": "revocation-fixture",
                "corpus_snapshot_id": "ss_" + "a" * 64,
                "capabilities": ["sparse"],
            },
        )
        self.registry.ready(self.a, "revocation-fixture", snapshot)
        conversation, run, citation, exported = (uuid.uuid4() for _ in range(4))
        with self.registry.connect() as db:
            db.execute(
                "UPDATE collections SET visibility='curated' WHERE collection_id=%s",
                ("revocation-fixture",),
            )
            db.execute(
                "INSERT INTO conversations(conversation_id,owner_id,collection_id,title) "
                "VALUES(%s,%s,'revocation-fixture','Synthetic')",
                (conversation, self.b),
            )
            db.execute(
                "INSERT INTO research_runs(run_id,conversation_id,owner_id,collection_id,"
                "snapshot_id,original_question,effective_query,configuration,state,result) "
                "VALUES(%s,%s,%s,'revocation-fixture',%s,'question','question',%s,'completed',%s)",
                (run, conversation, self.b, snapshot, Jsonb({}), Jsonb({"answer": "synthetic"})),
            )
            db.execute(
                "INSERT INTO evidence_citations(citation_id,run_id,chunk_id,evidence) "
                "VALUES(%s,%s,'synthetic',%s)",
                (citation, run, Jsonb({"text": "retained synthetic passage"})),
            )
            db.execute(
                "INSERT INTO exports(export_id,run_id,storage_key,media_type,content,"
                "extension,expires_at) VALUES(%s,%s,'synthetic','application/json',"
                "'{}','json',clock_timestamp()+interval '1 hour')",
                (exported, run),
            )
            event(db, run, "completed")
        paths = [
            f"/api/v1/runs/{run}",
            f"/api/v1/runs/{run}/events",
            f"/api/v1/conversations/{conversation}/runs",
            f"/api/v1/citations/{citation}",
            f"/api/v1/exports/{exported}",
        ]
        self.user(self.b)
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(verify_sources.call_count, 1)
        self.user(self.a)
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 404)
        with self.registry.connect() as db:
            db.execute(
                "UPDATE collections SET visibility='private' WHERE collection_id=%s",
                ("revocation-fixture",),
            )
        self.user(self.b)
        for path in paths:
            response = self.client.get(path, headers={"Last-Event-ID": "1"})
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("retained synthetic passage", response.text)
        self.assertEqual(verify_sources.call_count, 1)
        with patch("retrievec.app.search.RPCClient") as rpc:
            response = self.client.post(
                "/api/v1/search",
                headers=self.headers,
                json={
                    "collection_id": "revocation-fixture",
                    "snapshot_id": snapshot,
                    "query": "retained synthetic passage",
                    "retrieval": "sparse",
                },
            )
            self.assertEqual(response.status_code, 404)
            rpc.assert_not_called()

    def test_saved_history_idempotency_replay_and_isolation(self):
        from retrievec.app.generation import ProviderConfig
        from retrievec.corpus.snapshot import canonical

        self.app.state.providers = {
            "local": ProviderConfig("local", "http://127.0.0.1:8095", "fixture", "test-only")
        }
        self.user(self.a)
        collection = self.client.post(
            "/api/v1/collections", json={"title": "Research"}, headers=self.headers
        ).json()["collection_id"]
        manifest = {
            "schema_version": 1,
            "collection_id": collection,
            "corpus_snapshot_id": "ss_" + "a" * 64,
            "capabilities": ["sparse"],
        }
        pinned = self.registry.register(self.a, manifest)
        folder = self.app.state.settings.store / "snapshots" / pinned
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        self.registry.ready(self.a, collection, pinned)
        self.registry.activate(self.a, collection, pinned, None)
        conversation = self.client.post(
            "/api/v1/conversations",
            headers=self.headers,
            json={"collection_id": collection, "title": "Evidence"},
        ).json()["conversation_id"]
        path = f"/api/v1/conversations/{conversation}/runs"
        payload = {"question": "What works?", "retrieval": "sparse"}
        headers = {**self.headers, "Idempotency-Key": "first"}
        response = self.client.post(path, json=payload, headers=headers)
        self.assertEqual(response.status_code, 202, response.text)
        first = response.json()
        self.assertEqual(first["snapshot_id"], pinned)
        rewrite_url = f"/api/v1/runs/{first['run_id']}/rewrite"
        preview = self.client.post(rewrite_url, json={"question": "And why?"}, headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(
            preview.json()["effective_query"],
            "Previous question: What works?\nFollow-up question: And why?",
        )
        self.user(self.b)
        self.assertEqual(
            self.client.post(
                rewrite_url, json={"question": "And why?"}, headers=self.headers
            ).status_code,
            404,
        )
        self.user(self.a)
        self.assertEqual(
            self.client.post(path, json=payload, headers=headers).json()["run_id"], first["run_id"]
        )
        self.assertEqual(
            self.client.post(
                path, json={**payload, "question": "Different"}, headers=headers
            ).status_code,
            409,
        )
        replay = self.client.post(
            path,
            json={**payload, "parent_run": first["run_id"], "snapshot": "historical"},
            headers={**self.headers, "Idempotency-Key": "replay"},
        )
        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertNotEqual(first["run_id"], replay.json()["run_id"])
        self.assertEqual(len(self.client.get(path).json()), 2)
        saved = f"/api/v1/collections/{collection}/runs"
        first_page = self.client.get(saved, params={"q": "works", "limit": 1}).json()
        self.assertEqual(len(first_page["items"]), 1)
        self.assertNotIn("result", first_page["items"][0])
        second_page = self.client.get(
            saved, params={"q": "works", "limit": 1, "before": first_page["next_cursor"]}
        ).json()
        self.assertEqual(len(second_page["items"]), 1)
        self.assertIsNone(second_page["next_cursor"])
        self.assertNotEqual(first_page["items"][0]["run_id"], second_page["items"][0]["run_id"])
        self.assertEqual(self.client.get(saved, params={"q": "%"}).json()["items"], [])
        self.assertEqual(self.client.get(saved, params={"limit": 101}).status_code, 422)
        from retrievec.app.run_state import RunState

        state = RunState(self.registry)
        claimed = state.claim()
        self.assertEqual(str(claimed["run_id"]), first["run_id"])
        self.assertFalse(state.progress(claimed, "evidence_ready", {"evidence": []}))
        self.assertTrue(state.transition(claimed, "generating"))
        with self.registry.connect() as db:
            stage_time = db.execute(
                "SELECT stage_started_at FROM research_runs WHERE run_id=%s", (claimed["run_id"],)
            ).fetchone()["stage_started_at"]
        self.assertTrue(state.progress(claimed, "evidence_ready", {"evidence": []}))
        with self.registry.connect() as db:
            self.assertEqual(
                db.execute(
                    "SELECT stage_started_at FROM research_runs WHERE run_id=%s",
                    (claimed["run_id"],),
                ).fetchone()["stage_started_at"],
                stage_time,
            )
        replacement = {**manifest, "corpus_snapshot_id": "ss_" + "b" * 64}
        next_snapshot = self.registry.register(self.a, replacement)
        next_folder = self.app.state.settings.store / "snapshots" / next_snapshot
        next_folder.mkdir(parents=True)
        (next_folder / "manifest.json").write_bytes(canonical(replacement) + b"\n")
        self.registry.ready(self.a, collection, next_snapshot)
        self.registry.activate(self.a, collection, next_snapshot, pinned)
        self.assertEqual(
            self.client.get("/api/v1/runs/" + first["run_id"]).json()["snapshot_id"], pinned
        )
        # Restore the current pointer for the later missing-artifact assertion.
        self.registry.activate(self.a, collection, pinned, next_snapshot)
        events = self.client.get(f"/api/v1/runs/{first['run_id']}/events").text
        self.assertIn("event: queued", events)
        self.assertIn("event: retrieving", events)
        resumed = self.client.get(f"/api/v1/runs/{first['run_id']}/events?after=1").text
        self.assertNotIn("event: queued", resumed)
        self.client.post(f"/api/v1/runs/{first['run_id']}/cancel", headers=self.headers)
        self.assertFalse(state.transition(claimed, "generating"))
        self.assertFalse(state.heartbeat(claimed))
        self.assertFalse(state.progress(claimed, "evidence_ready", {"evidence": []}))
        self.user(self.b)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get(saved).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/runs/" + first["run_id"]).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/runs/{first['run_id']}/events").status_code, 404)
        self.user(self.a)
        (folder / "manifest.json").unlink()
        response = self.client.post(
            path, json=payload, headers={**self.headers, "Idempotency-Key": "missing"}
        )
        self.assertEqual(response.json()["code"], "artifact_unavailable")
        (folder / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        cloud = ProviderConfig(
            "cloud", "https://example.invalid", "fixture", "test-only", cloud=True
        )
        self.app.state.providers["cloud"] = cloud
        self.assertEqual(
            self.client.post(
                rewrite_url,
                json={"question": "And why?", "provider": "cloud"},
                headers=self.headers,
            ).status_code,
            403,
        )
        cloud_payload = {**payload, "provider": "cloud"}
        cloud_headers = {**self.headers, "Idempotency-Key": "cloud"}
        self.assertEqual(
            self.client.post(path, json=cloud_payload, headers=cloud_headers).status_code, 403
        )
        consent = f"/api/v1/collections/{collection}/providers/cloud/consent"
        self.user(self.b)
        self.assertEqual(self.client.put(consent, headers=self.headers).status_code, 404)
        self.user(self.a)
        self.assertEqual(self.client.put(consent, headers=self.headers).status_code, 204)
        cloud_run = self.client.post(path, json=cloud_payload, headers=cloud_headers)
        self.assertEqual(cloud_run.status_code, 202, cloud_run.text)
        state.cancel(self.a, replay.json()["run_id"])
        cloud_claim = state.claim()
        self.assertEqual(str(cloud_claim["run_id"]), cloud_run.json()["run_id"])
        self.assertTrue(state.transition(cloud_claim, "generating"))
        self.client.delete(consent, headers=self.headers)
        with self.assertRaises(PermissionError):
            state.transition(cloud_claim, "validating")
        self.assertEqual(
            self.client.get("/api/v1/runs/" + cloud_run.json()["run_id"]).json()["state"],
            "cancelled",
        )

        # Materialized exports remain private and expire independently of saved runs.
        from psycopg.types.json import Jsonb

        with self.registry.connect() as db:
            db.execute(
                "UPDATE research_runs SET state='completed',result=%s WHERE run_id=%s",
                (
                    Jsonb(
                        {
                            "answer": {
                                "status": "insufficient_evidence",
                                "claims": [],
                                "comparisons": [],
                                "limitations": [],
                            },
                            "evidence": [],
                        }
                    ),
                    first["run_id"],
                ),
            )
        exported = self.client.post(
            f"/api/v1/runs/{first['run_id']}/exports", json={"format": "json"}, headers=self.headers
        )
        self.assertEqual(exported.status_code, 201, exported.text)
        download = exported.json()["download_url"]
        self.assertEqual(self.client.get(download).status_code, 200)
        self.user(self.b)
        self.assertEqual(self.client.get(download).status_code, 404)
        self.user(self.a)
        with self.registry.connect() as db:
            db.execute(
                "UPDATE exports SET expires_at=clock_timestamp()-interval '1 second' "
                "WHERE export_id=%s",
                (exported.json()["export_id"],),
            )
        self.assertEqual(self.client.get(download).status_code, 410)
        self.client.delete("/api/v1/collections/" + collection, headers=self.headers)
        self.assertEqual(self.client.get(f"/api/v1/runs/{first['run_id']}/events").status_code, 404)
        with self.registry.connect() as db:
            self.assertEqual(
                db.execute(
                    "SELECT state FROM research_runs WHERE run_id=%s", (replay.json()["run_id"],)
                ).fetchone()["state"],
                "cancelled",
            )

    def test_upload_job_isolation_and_archive_cancellation(self):
        self.user(self.a)
        collection = self.client.post(
            "/api/v1/collections", json={"title": "Upload"}, headers=self.headers
        ).json()["collection_id"]
        url = "/api/v1/collections/" + collection + "/uploads"
        response = self.client.post(
            url,
            files={"files": ("paper.txt", b"Dense retrieval evidence")},
            headers={**self.headers, "Idempotency-Key": "upload-1"},
        )
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["job_id"]
        self.assertEqual(self.client.get("/api/v1/jobs/" + job_id).json()["state"], "queued")
        self.user(self.b)
        self.assertEqual(self.client.get("/api/v1/jobs/" + job_id).status_code, 404)
        with patch("retrievec.app.search.RPCClient") as rpc:
            self.assertEqual(
                self.client.post(
                    "/api/v1/search",
                    json={"collection_id": collection, "query": "private evidence"},
                    headers=self.headers,
                ).status_code,
                404,
            )
            rpc.assert_not_called()
        with self.registry.connect() as db:
            source = db.execute(
                "SELECT source_id FROM upload_sources WHERE job_id=%s", (job_id,)
            ).fetchone()["source_id"]
        self.assertEqual(
            self.client.get(
                f"/api/v1/sources/{source}", params={"snapshot_id": "rs_" + "a" * 64}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                url,
                files={"files": ("paper.txt", b"stolen")},
                headers={**self.headers, "Idempotency-Key": "upload-2"},
            ).status_code,
            404,
        )
        self.user(self.a)
        self.client.delete("/api/v1/collections/" + collection, headers=self.headers)
        self.assertEqual(self.client.get("/api/v1/jobs/" + job_id).status_code, 404)
        with self.registry.connect() as db:
            row = db.execute(
                "SELECT state FROM ingestion_jobs WHERE job_id=%s", (job_id,)
            ).fetchone()
            self.assertEqual(row["state"], "cancelled")
        self.assertEqual(
            self.client.post(
                f"/api/v1/collections/{collection}/restore", headers=self.headers
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/v1/jobs/" + job_id).json()["state"], "cancelled")
