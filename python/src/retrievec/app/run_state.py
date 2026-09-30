"""Short transactions and fenced publication; no inference inside a transaction."""

from psycopg.types.json import Jsonb

from retrievec.app.resources import Resources

ACTIVE = ("queued", "retrieving", "generating", "validating")
NEXT = {"retrieving": "generating", "generating": "validating", "validating": "completed"}


def event(db, run_id, kind, payload=None):
    row = db.execute(
        "SELECT event_sequence,extract(epoch FROM (clock_timestamp()-stage_started_at))*1000 "
        "AS stage_elapsed_ms FROM research_runs WHERE run_id=%s FOR UPDATE",
        (run_id,),
    ).fetchone()
    sequence = row["event_sequence"] + 1
    db.execute(
        "UPDATE research_runs SET event_sequence=%s,stage_started_at=clock_timestamp() "
        "WHERE run_id=%s",
        (sequence, run_id),
    )
    db.execute(
        "INSERT INTO run_events(run_id,event_id,type,payload) VALUES(%s,%s,%s,%s)",
        (
            run_id,
            sequence,
            kind,
            Jsonb(
                {
                    **(payload or {"state": kind}),
                    "previous_stage_elapsed_ms": max(0, float(row["stage_elapsed_ms"])),
                }
            ),
        ),
    )


class RunState:
    def __init__(self, registry):
        self.registry = registry
        self.policy = Resources(registry)

    def access(self, db, run):
        self.policy.collection(db, run["owner_id"], run["collection_id"], lock=True)
        config = run["configuration"]
        if (
            config["generation"]["cloud"]
            and not db.execute(
                "SELECT 1 FROM provider_consents WHERE collection_id=%s AND provider_hash=%s",
                (run["collection_id"], config["provider_hash"]),
            ).fetchone()
        ):
            raise PermissionError("provider consent revoked")

    def claim(self):
        with self.registry.connect() as db:
            # Never repeat an uncertain provider call automatically after a crash.
            expired = db.execute(
                "UPDATE research_runs SET state='failed',error_code='worker_interrupted',"
                "fencing_token=fencing_token+1,lease_until=NULL "
                "WHERE state IN ('retrieving','generating','validating') "
                "AND lease_until < clock_timestamp() RETURNING run_id",
            ).fetchall()
            for row in expired:
                event(
                    db, row["run_id"], "failed", {"state": "failed", "code": "worker_interrupted"}
                )
            row = db.execute(
                "SELECT r.* FROM research_runs r JOIN collections c USING(collection_id) "
                "WHERE r.state='queued' AND NOT c.archived AND "
                "(c.owner_id=r.owner_id OR c.visibility='curated') "
                "ORDER BY r.created_at FOR UPDATE OF r SKIP LOCKED LIMIT 1",
            ).fetchone()
            if row is None:
                return None
            result = db.execute(
                "UPDATE research_runs SET state='retrieving',attempts=attempts+1,"
                "fencing_token=fencing_token+1,lease_until=clock_timestamp()+interval '30 seconds' "
                "WHERE run_id=%s RETURNING *",
                (row["run_id"],),
            ).fetchone()
            event(db, row["run_id"], "retrieving")
            return result

    def heartbeat(self, run):
        with self.registry.connect() as db:
            self.access(db, run)
            return (
                db.execute(
                    "UPDATE research_runs SET lease_until=clock_timestamp()+interval '30 seconds' "
                    "WHERE run_id=%s AND fencing_token=%s AND lease_until>clock_timestamp() "
                    "AND state IN ('retrieving','generating','validating') RETURNING run_id",
                    (run["run_id"], run["fencing_token"]),
                ).fetchone()
                is not None
            )

    def transition(self, run, state, *, result=None, code=None, evidence=()):
        with self.registry.connect() as db:
            self.access(db, run)
            row = db.execute(
                "SELECT * FROM research_runs WHERE run_id=%s FOR UPDATE", (run["run_id"],)
            ).fetchone()
            if (
                row["fencing_token"] != run["fencing_token"]
                or row["state"] not in ACTIVE
                or (state != "failed" and NEXT.get(row["state"]) != state)
            ):
                return False
            updated = db.execute(
                "UPDATE research_runs SET state=%s,result=%s,error_code=%s,"
                "lease_until=CASE WHEN %s THEN NULL ELSE lease_until END "
                "WHERE run_id=%s AND lease_until>clock_timestamp() RETURNING run_id",
                (
                    state,
                    Jsonb(result) if result is not None else None,
                    code,
                    state in ("completed", "failed"),
                    run["run_id"],
                ),
            ).fetchone()
            if updated is None:
                return False
            for item in evidence:
                db.execute(
                    "INSERT INTO evidence_citations(citation_id,run_id,chunk_id,evidence) "
                    "VALUES(%s,%s,%s,%s)",
                    (item["citation_id"], run["run_id"], item["chunk_id"], Jsonb(item)),
                )
            event(db, run["run_id"], state)
            return True

    def cancel(self, user, run_id):
        with self.registry.connect() as db:
            run = self.policy.owned(db, user, "run", run_id)
            self.policy.collection(db, user, run["collection_id"], lock=True)
            row = db.execute(
                "UPDATE research_runs SET state='cancelled',fencing_token=fencing_token+1,"
                "lease_until=NULL WHERE run_id=%s AND state IN "
                "('queued','retrieving','generating','validating') RETURNING run_id",
                (run_id,),
            ).fetchone()
            if row:
                event(db, run_id, "cancelled")

    def progress(self, run, kind, payload):
        """Publish bounded provisional events without resetting stage timing."""
        if kind not in ("evidence_ready", "draft_delta"):
            raise ValueError("unsupported progress event")
        with self.registry.connect() as db:
            self.access(db, run)
            row = db.execute(
                "UPDATE research_runs SET event_sequence=event_sequence+1 "
                "WHERE run_id=%s AND fencing_token=%s AND state='generating' "
                "AND lease_until>clock_timestamp() AND event_sequence<2048 "
                "RETURNING event_sequence",
                (run["run_id"], run["fencing_token"]),
            ).fetchone()
            if row is None:
                return False
            db.execute(
                "INSERT INTO run_events(run_id,event_id,type,payload) VALUES(%s,%s,%s,%s)",
                (run["run_id"], row["event_sequence"], kind, Jsonb(payload)),
            )
            return True
