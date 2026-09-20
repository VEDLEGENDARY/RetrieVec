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

    def test_session_expiry_and_no_resurrection(self):
        token = self.tokens[self.a]
        self.sessions.save(token, "", {})
        self.sessions.save(token, token, {"principal": self.a})
        self.assertEqual(self.sessions.load(token), {})
        self.assertEqual(self.sessions.identity("test-issuer", "a" + token[1:]), self.a)

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
        from retrievec.app.run_state import RunState

        state = RunState(self.registry)
        claimed = state.claim()
        self.assertEqual(str(claimed["run_id"]), first["run_id"])
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
        self.user(self.b)
        self.assertEqual(self.client.get(path).status_code, 404)
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
