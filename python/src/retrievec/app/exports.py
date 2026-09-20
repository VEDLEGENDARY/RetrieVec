"""Exports are materialized from stored results and remain authenticated."""

import csv
import io
import json
import re
import uuid
from typing import Literal

from fastapi import Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from retrievec.app.auth import principal
from retrievec.app.errors import APIError


def markdown(text):
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", str(text)).replace("\r", "")


def bibtex(text):
    escapes = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return (
        "".join(escapes.get(char, char) for char in str(text)).replace("\n", " ").replace("\r", " ")
    )


def cell(value):
    text = "" if value is None else str(value)
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
        or text.startswith(("\t", "\r", "\n"))
        else text
    )


def render(run, format):
    result = run["result"]
    evidence, answer = result["evidence"], result["answer"]
    if format == "json":
        public = {
            key: run[key]
            for key in (
                "run_id",
                "snapshot_id",
                "original_question",
                "effective_query",
                "configuration",
                "parent_run",
                "created_at",
                "result",
            )
        }
        return (
            json.dumps({"schema_version": 1, **public}, default=str, ensure_ascii=False, indent=2),
            "application/json",
            "json",
        )
    if format == "markdown":
        lines = [
            "# Research run",
            "",
            markdown(run["original_question"]),
            "",
            "Status: " + answer["status"],
            "",
            "Structural checks only; human review pending.",
            "",
        ]
        lines += [
            "- " + markdown(claim["text"]) + " (" + ", ".join(claim["evidence_ids"]) + ")"
            for claim in answer["claims"]
        ]
        for row in answer["comparisons"]:
            lines += ["", "## Comparison"] + [
                markdown(key) + ": " + markdown(value) for key, value in row.items()
            ]
        lines += ["", "## Evidence"]
        for item in evidence:
            lines += [
                "",
                markdown(item["evidence_id"] + ": " + item["title"]),
                "Pages: " + markdown(item.get("page_range")),
                "",
                markdown(item["text"]),
            ]
        lines += ["", "## Limitations"] + ["- " + markdown(item) for item in answer["limitations"]]
        lines += [
            "",
            "Snapshot: " + run["snapshot_id"],
            "Model: " + markdown(run["configuration"]["generation"]["model"]),
            "Revision: " + markdown(run["configuration"]["generation"]["revision"]),
        ]
        return "\n".join(lines) + "\n", "text/markdown", "md"
    if format == "bibtex":
        papers = {item["paper_version_id"]: item for item in evidence}
        entries = []
        for key, item in papers.items():
            safe_key = re.sub(r"[^a-zA-Z0-9]", "", key)
            fields = ["  title = {" + bibtex(item["title"]) + "}"]
            if item.get("authors"):
                fields.append(
                    "  author = {" + " and ".join(bibtex(a) for a in item["authors"]) + "}"
                )
            entries.append("@misc{" + safe_key + ",\n" + ",\n".join(fields) + "\n}")
        return "\n\n".join(entries) + "\n", "application/x-bibtex", "bib"
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        columns = [
            "evidence_id",
            "paper_id",
            "title",
            "page_range",
            "rank",
            "bm25_score",
            "cosine_score",
            "rrf_score",
            "text",
        ]
        writer.writerow(["snapshot_id", *columns])
        for item in evidence:
            writer.writerow([cell(run["snapshot_id"]), *[cell(item.get(key)) for key in columns]])
        return output.getvalue(), "text/csv", "csv"
    raise ValueError("unsupported export format")


class ExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["markdown", "bibtex", "json", "csv"]


def install_exports(app):
    registry, policy = app.state.registry, app.state.resources

    @app.get("/api/v1/citations/{citation_id}")
    def citation(citation_id: uuid.UUID, request: Request):
        with registry.connect() as db:
            row = policy.owned(db, principal(request), "citation", citation_id)
            run = policy.owned(db, principal(request), "run", row["run_id"])
        from retrievec.app.research_worker import ResearchWorker

        try:
            ResearchWorker(registry, app.state.settings, providers={}).verify_sources(
                run, [row["evidence"]]
            )
        except (OSError, ValueError):
            raise APIError(
                409, "source_unavailable", "Retained evidence or original source is unavailable"
            ) from None
        with registry.connect() as db:
            policy.owned(db, principal(request), "citation", citation_id)
        return {**row["evidence"], "snapshot_id": run["snapshot_id"]}

    @app.post("/api/v1/runs/{run_id}/exports", status_code=201)
    def create(run_id: uuid.UUID, value: ExportInput, request: Request):
        user = principal(request)
        with registry.connect() as db:
            run = policy.owned(db, user, "run", run_id)
            policy.collection(db, user, run["collection_id"], lock=True)
            if run["state"] != "completed" or run["result"] is None:
                raise APIError(409, "run_incomplete", "Export a completed run")
            # Keep export storage bounded per run; expired records are disposable.
            db.execute(
                "DELETE FROM exports WHERE run_id=%s AND expires_at<clock_timestamp()", (run_id,)
            )
            count = db.execute(
                "SELECT count(*) AS count FROM exports WHERE run_id=%s", (run_id,)
            ).fetchone()["count"]
            if count >= 20:
                raise APIError(409, "export_capacity", "Reuse a recent download or wait for expiry")
            content, media_type, extension = render(run, value.format)
            identity = uuid.uuid4()
            row = db.execute(
                "INSERT INTO exports(export_id,run_id,storage_key,media_type,content,"
                "extension,expires_at) VALUES(%s,%s,%s,%s,%s,%s,"
                "clock_timestamp()+interval '20 minutes') "
                "RETURNING export_id,expires_at",
                (identity, run_id, identity.hex, media_type, content, extension),
            ).fetchone()
            return {**row, "download_url": f"/api/v1/exports/{identity}"}

    @app.get("/api/v1/exports/{export_id}")
    def download(export_id: uuid.UUID, request: Request):
        with registry.connect() as db:
            row = policy.owned(db, principal(request), "export", export_id)
            valid = db.execute(
                "SELECT 1 FROM exports WHERE export_id=%s AND expires_at>clock_timestamp()",
                (export_id,),
            ).fetchone()
            if (
                not valid
                or row["content"] is None
                or row["extension"] not in ("md", "bib", "json", "csv")
            ):
                raise APIError(410, "export_expired", "Create a new export from the saved run")
        return Response(
            row["content"],
            media_type=row["media_type"],
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": (
                    f'attachment; filename="research-{export_id}.{row["extension"]}"'
                ),
            },
        )
