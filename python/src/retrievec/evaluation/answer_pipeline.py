"""Sequential, authenticated answer evaluation through the product API."""

import asyncio
import copy
import time
import uuid
from urllib.parse import quote, urlsplit

import httpx

from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.answer_quality import load_dataset, summarize


async def evaluate(args, session, corpus, *, transport=None, checkpoint=None, resume=None):
    address = urlsplit(args.origin)
    if (
        address.scheme != "http"
        or address.hostname not in ("127.0.0.1", "localhost", "::1")
        or address.username
        or address.password
        or address.query
        or address.fragment
        or address.path not in ("", "/")
    ):
        raise ValueError("evaluation requires a loopback workspace origin")
    dataset, sources = load_dataset(args.dataset)
    manifest, papers, _ = corpus
    if {p["paper_id"]: p["source_sha256"] for p in papers} != sources:
        raise ValueError("snapshot papers do not match the fixed corpus manifest")
    if manifest["collection_id"] != args.collection:
        raise ValueError("local corpus differs from requested collection")
    if not 1 <= args.timeout <= 600:
        raise ValueError("timeout must be between 1 and 600 seconds")
    report = {
        "schema_version": 1,
        "dataset_sha256": digest(canonical(dataset)),
        "dataset_id": dataset["dataset_id"],
        "split": args.split,
        "snapshot_id": args.snapshot,
        "collection_id": args.collection,
        "question_provenance": "synthetic-question",
        "assessment": "automatic-only",
        "providers": {},
        "cases": [],
        "complete": False,
        "nli_check": "NOT run",
        "limitations": [
            "Synthetic template expectations are not human judgments.",
            "No semantic score is available without human review or an explicitly labeled judge.",
            "TTFT excludes queue time; end-to-end latency includes polling.",
        ],
    }
    async with httpx.AsyncClient(
        base_url=args.origin.rstrip("/"),
        transport=transport,
        timeout=30,
        follow_redirects=False,
        cookies={"retrievec_session": session["session_cookie"]},
        headers={"Origin": args.origin.rstrip("/"), "X-CSRF-Token": session["csrf_token"]},
    ) as client:

        async def request(method, path, **kwargs):
            response = await client.request(method, path, **kwargs)
            if response.status_code >= 300:
                # Avoid persisting cookies, request headers, or provider exception bodies.
                raise ValueError(f"product API returned HTTP {response.status_code}")
            return response.json()

        await request("GET", "/api/v1/me")
        collections = await request("GET", "/api/v1/collections")
        selected = next(
            (row for row in collections if row["collection_id"] == args.collection), None
        )
        if selected is None or selected["active_snapshot"] != args.snapshot:
            raise ValueError("authorized active snapshot differs from evaluation snapshot")
        providers = await request(
            "GET", f"/api/v1/collections/{quote(args.collection, safe='')}/providers"
        )
        available = {row["name"]: row for row in providers}
        if not 1 <= len(args.providers) <= 2 or len(set(args.providers)) != len(args.providers):
            raise ValueError("select one or two distinct configured providers")
        for name in args.providers:
            config = available.get(name)
            if config is None or not config["consented"]:
                raise ValueError("selected provider is unavailable or lacks existing consent")
            report["providers"][name] = config
        local = report["providers"][args.providers[0]]
        if (
            local["cloud"]
            or "qwen2.5" not in local["model"].lower()
            or "1.5b" not in local["model"].lower()
        ):
            raise ValueError("first provider must be local Qwen2.5 1.5B")
        report["stronger_provider_comparison"] = (
            "pending: user requested Qwen2.5 1.5B only for this run"
            if len(args.providers) == 1
            else "configured comparison; strength is an operator assertion"
        )
        questions = [row for row in dataset["questions"] if row["split"] == args.split]
        expected_ids = {
            f"{name}/{question['id']}" for name in args.providers for question in questions
        }
        if resume is not None:
            for key in (
                "schema_version",
                "dataset_sha256",
                "split",
                "snapshot_id",
                "collection_id",
                "providers",
            ):
                if resume.get(key) != report[key]:
                    raise ValueError("resume report differs: " + key)
            prior = [case["case_id"] for case in resume["cases"]]
            if len(prior) != len(set(prior)) or not set(prior) <= expected_ids:
                raise ValueError("resume contains duplicate or foreign cases")
            report = copy.deepcopy(resume)
            report["complete"] = False
        recorded_ids = {case["case_id"] for case in report["cases"]}
        for name in args.providers:
            if all(f"{name}/{question['id']}" in recorded_ids for question in questions):
                continue
            conversation = await request(
                "POST",
                "/api/v1/conversations",
                json={
                    "collection_id": args.collection,
                    "title": f"Answer evaluation: {args.split} / {name}",
                },
            )
            for question in questions:
                if f"{name}/{question['id']}" in recorded_ids:
                    continue
                started = time.perf_counter()
                case = {
                    "case_id": f"{name}/{question['id']}",
                    "provider": name,
                    "question": question["question"],
                    "question_kind": question["kind"],
                    "judgment_provenance": question["judgment_provenance"],
                    "state": "failed",
                    "human_review": None,
                    "llm_judge": None,
                }
                run = None
                try:
                    run = await request(
                        "POST",
                        f"/api/v1/conversations/{conversation['conversation_id']}/runs",
                        headers={"Idempotency-Key": str(uuid.uuid4())},
                        json={
                            "question": question["question"],
                            "provider": name,
                            "retrieval": "hybrid",
                        },
                    )
                    case["run_id"] = run["run_id"]
                    deadline = time.monotonic() + args.timeout
                    while run["state"] not in ("completed", "failed", "cancelled"):
                        if time.monotonic() >= deadline:
                            await client.post(f"/api/v1/runs/{run['run_id']}/cancel")
                            raise ValueError(
                                "run exceeded evaluation deadline; cancellation requested"
                            )
                        await asyncio.sleep(0.25)
                        run = await request("GET", f"/api/v1/runs/{run['run_id']}")
                    if run["snapshot_id"] != args.snapshot:
                        raise ValueError("run snapshot changed")
                    if run["configuration"]["provider_hash"] != available[name]["identity"]:
                        raise ValueError("provider identity changed")
                    if run["state"] != "completed":
                        case["error_code"] = run.get("error_code")
                        raise ValueError(f"run ended as {run['state']}")
                    result = run["result"]
                    for evidence in result["evidence"]:
                        if sources.get(evidence["paper_id"]) != evidence["source_sha256"]:
                            raise ValueError("evidence source is outside fixed manifest")
                    case.update(state="completed", result=result)
                except (ValueError, httpx.HTTPError) as error:
                    case["error"] = (
                        str(error) if isinstance(error, ValueError) else "product transport failed"
                    )
                case["elapsed_ms"] = (time.perf_counter() - started) * 1000
                report["cases"].append(case)
                if checkpoint:
                    checkpoint(summarize(report))
    report["complete"] = {case["case_id"] for case in report["cases"]} == expected_ids
    report["all_runs_completed"] = all(row["state"] == "completed" for row in report["cases"])
    return summarize(report)
