"""Offline metadata/artifact bundles and restores into fresh rehearsal databases.

Bundles contain private evidence and must stay in owner-controlled storage.
Session rows are deliberately excluded; restoration never resumes a browser session.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from retrievec.corpus.snapshot import canonical
from retrievec.registry.retention import audit_retained


def checksum(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def inventory(root):
    root = Path(root)
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        raise ValueError("artifact root must be a real directory")
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise ValueError("linked artifact paths cannot be backed up")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("unsupported artifact entry")
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": checksum(path),
            }
        )
    return result


def metadata_fingerprint(db):
    db.execute("SET LOCAL TIME ZONE 'UTC'")
    # Include ownership, retained snapshots, sources and saved answers, but not sessions.
    queries = {
        "migrations": "SELECT * FROM schema_migrations ORDER BY version",
        "principals": "SELECT * FROM principals ORDER BY principal_id",
        "identities": "SELECT * FROM identities ORDER BY issuer,subject",
        "conversations": "SELECT * FROM conversations ORDER BY conversation_id",
        "jobs": "SELECT * FROM ingestion_jobs ORDER BY job_id",
        "run_events": "SELECT * FROM run_events ORDER BY run_id,event_id",
        "provider_consents": "SELECT * FROM provider_consents ORDER BY collection_id,provider_hash",
        "papers": "SELECT * FROM paper_versions ORDER BY paper_version_id",
        "collection_papers": "SELECT * FROM collection_papers ORDER BY collection_id,paper_id",
        "collections": "SELECT collection_id,owner_id,visibility,active_snapshot,archived "
        "FROM collections ORDER BY collection_id",
        "snapshots": "SELECT snapshot_id,collection_id,corpus_snapshot_id,manifest,state "
        "FROM retrieval_snapshots ORDER BY snapshot_id",
        "sources": "SELECT source_id,collection_id,owner_id,storage_key,source_hash "
        "FROM upload_sources ORDER BY source_id",
        "runs": "SELECT run_id,owner_id,collection_id,snapshot_id,state,result "
        "FROM research_runs ORDER BY run_id",
        "citations": "SELECT * FROM evidence_citations ORDER BY citation_id",
        "exports": "SELECT * FROM exports ORDER BY export_id",
    }
    result = {}
    for name, query in queries.items():
        rows = db.execute(query).fetchall()
        raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str).encode()
        result[name] = {"rows": len(rows), "sha256": hashlib.sha256(raw).hexdigest()}
    return result


def pg_tool(program, dsn, arguments):
    executable = shutil.which(program)
    if not executable:
        raise ValueError("PostgreSQL 18 client tools must be on PATH")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    fields = {
        "host": "PGHOST",
        "hostaddr": "PGHOSTADDR",
        "port": "PGPORT",
        "dbname": "PGDATABASE",
        "user": "PGUSER",
        "password": "PGPASSWORD",
        "passfile": "PGPASSFILE",
        "sslmode": "PGSSLMODE",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "sslrootcert": "PGSSLROOTCERT",
        "sslcrl": "PGSSLCRL",
        "options": "PGOPTIONS",
        "channel_binding": "PGCHANNELBINDING",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "application_name": "PGAPPNAME",
        "target_session_attrs": "PGTARGETSESSIONATTRS",
        "gssencmode": "PGGSSENCMODE",
    }
    connection = conninfo_to_dict(dsn)
    if set(connection) - set(fields):
        raise ValueError("backup requires an explicit DSN using supported libpq fields")
    for key, value in connection.items():
        environment[fields[key]] = value
    environment["PGCONNECT_TIMEOUT"] = "10"
    result = subprocess.run(
        [executable, *arguments], env=environment, capture_output=True, timeout=1800, check=False
    )
    if result.returncode:
        # PostgreSQL errors can contain private data; never include them in public reports.
        raise RuntimeError("PostgreSQL backup tool failed; bundle is incomplete")


def disjoint(left, right):
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        raise ValueError("backup and artifact roots must be separate")


def backup(dsn, store, destination, *, quiesced=False):
    if not quiesced:
        raise ValueError("stop all workspace writers and explicitly acknowledge quiescence")
    store, destination = Path(store).resolve(), Path(destination).resolve()
    disjoint(store, destination)
    if destination.exists():
        raise ValueError("backup destination must not exist")
    files = inventory(store)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "INCOMPLETE").write_text("Do not restore until manifest.json exists.\n")
    with psycopg.connect(dsn, row_factory=dict_row) as db:
        if not 180000 <= db.info.server_version < 190000:
            raise ValueError("PostgreSQL 18 is required")
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        active = db.execute(
            "SELECT (SELECT count(*) FROM ingestion_jobs WHERE state='running') + "
            "(SELECT count(*) FROM research_runs "
            "WHERE state IN ('retrieving','generating','validating')) AS n"
        ).fetchone()["n"]
        if active:
            raise ValueError("active work exists; finish recovery before taking an offline backup")
        database = db.execute("SELECT current_database() AS name").fetchone()["name"]
        snapshot = db.execute("SELECT pg_export_snapshot() AS id").fetchone()["id"]
        metadata = metadata_fingerprint(db)
        references = audit_retained(db, store, files)
        pg_tool(
            "pg_dump",
            dsn,
            [
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--exclude-table-data=*.browser_sessions",
                "--snapshot=" + snapshot,
                "--file=" + str(destination / "metadata.dump"),
            ],
        )
        artifacts = destination / "store"
        artifacts.mkdir()
        for row in files:
            target = artifacts / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(store / row["path"], target)
        if inventory(artifacts) != files or inventory(store) != files:
            raise ValueError("artifacts changed during backup")
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_database": database,
        "source_store": str(store),
        "session_rows": "excluded",
        "files": files,
        "metadata": metadata,
        "references": references,
        "dump_sha256": checksum(destination / "metadata.dump"),
    }
    (destination / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    (destination / "INCOMPLETE").unlink()
    return {"files": len(files), "metadata": metadata}


def verify(bundle):
    bundle = Path(bundle).resolve()
    if (bundle / "INCOMPLETE").exists():
        raise ValueError("incomplete backup")
    manifest_path, dump_path = bundle / "manifest.json", bundle / "metadata.dump"
    if (
        manifest_path.is_symlink()
        or dump_path.is_symlink()
        or not manifest_path.is_file()
        or not dump_path.is_file()
        or manifest_path.stat().st_size > 64 * 1024 * 1024
    ):
        raise ValueError("invalid backup manifest or dump")
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schema_version") != 1 or manifest.get("session_rows") != "excluded":
        raise ValueError("unsupported backup")
    if not isinstance(manifest.get("files"), list):
        raise ValueError("invalid backup inventory")
    seen = set()
    for row in manifest["files"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "bytes", "sha256"}
            or not isinstance(row["path"], str)
            or type(row["bytes"]) is not int
            or row["bytes"] < 0
            or not isinstance(row["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        ):
            raise ValueError("invalid artifact inventory entry")
        path = PurePosixPath(row["path"])
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in row["path"]
            or ":" in row["path"]
            or path.as_posix() != row["path"]
            or not path.parts
            or row["path"] in seen
        ):
            raise ValueError("unsafe artifact path")
        seen.add(row["path"])
    if inventory(bundle / "store") != manifest["files"]:
        raise ValueError("artifact inventory mismatch")
    if checksum(bundle / "metadata.dump") != manifest["dump_sha256"]:
        raise ValueError("metadata dump mismatch")
    return manifest


def restore(dsn, bundle, destination):
    bundle, destination = Path(bundle).resolve(), Path(destination).resolve()
    manifest = verify(bundle)
    if (
        not isinstance(manifest.get("source_store"), str)
        or not Path(manifest["source_store"]).is_absolute()
        or not isinstance(manifest.get("source_database"), str)
        or not isinstance(manifest.get("metadata"), dict)
        or not isinstance(manifest.get("references"), dict)
    ):
        raise ValueError("backup lacks restore provenance")
    disjoint(bundle, destination)
    disjoint(Path(manifest["source_store"]).resolve(), destination)
    if destination.exists():
        raise ValueError("restore artifact destination must not exist")
    with psycopg.connect(dsn, row_factory=dict_row) as db:
        if not 180000 <= db.info.server_version < 190000:
            raise ValueError("PostgreSQL 18 is required")
        name = db.execute("SELECT current_database() AS name").fetchone()["name"]
        if (
            not re.fullmatch(r"retrievec_restore_[0-9a-f]{32}", name)
            or name == manifest["source_database"]
        ):
            raise ValueError("target must be a new retrievec_restore_<32 hex> rehearsal database")
        if db.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
            "AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S') LIMIT 1"
        ).fetchone():
            raise ValueError("restore database must be empty")
    destination.mkdir(parents=True, exist_ok=False)
    # No --clean, --create or service startup: an interrupted rehearsal remains inspectable.
    for row in manifest["files"]:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle / "store" / row["path"], target)
    if inventory(destination) != manifest["files"]:
        raise ValueError("restored artifact mismatch")
    pg_tool(
        "pg_restore",
        dsn,
        [
            "--dbname=" + name,
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            "--exit-on-error",
            str(bundle / "metadata.dump"),
        ],
    )
    with psycopg.connect(dsn, row_factory=dict_row) as db:
        actual = metadata_fingerprint(db)
        if actual != manifest["metadata"]:
            raise ValueError("restored ownership or snapshot references differ")
        if audit_retained(db, destination, manifest["files"]) != manifest["references"]:
            raise ValueError("restored artifact graph differs")
        if db.execute("SELECT count(*) AS n FROM browser_sessions").fetchone()["n"]:
            raise ValueError("restore unexpectedly contains browser sessions")
    return {
        "database": name,
        "files": len(manifest["files"]),
        "metadata": actual,
        "services_started": False,
        "sessions_restored": False,
    }
