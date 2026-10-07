"""Frozen phase-3 controls over the original BEIR split and production kernels."""

import json
import os
import platform
import random
import statistics
import subprocess
import time
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest
from retrievec.dense.model import adapter
from retrievec.dense.parallel import run_legs
from retrievec.evaluation.beir_data import finish, order, prepare, qrels, rows
from retrievec.evaluation.beir_eval import score
from retrievec.evaluation.beir_reranker import CrossEncoder
from retrievec.evaluation.beir_runtime import Pipeline, SparseControl
from retrievec.evaluation.beir_variants import fuse_variant
from retrievec.evaluation.load import percentile
from retrievec.evaluation.paired import compare


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def freeze(path, value):
    if path.exists():
        if json.loads(path.read_bytes()) != value:
            raise ValueError(f"frozen artifact differs: {path}; use a new work directory")
    else:
        save(path, value)
    return value


def committed(root, path):
    relative = path.resolve().relative_to(root).as_posix()
    value = json.loads(path.read_bytes())
    frozen = json.loads(subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=root))
    if frozen != value:
        raise ValueError("commit the protocol before running the study")
    return value


def measured_row(pipeline, qid, hits, elapsed, judgments, **extra):
    ranking = pipeline.documents(hits, qid)
    return dict(
        query_id=qid, ranking=ranking, elapsed_ms=elapsed, **score(ranking, judgments[qid]), **extra
    )


def report_run(name, config, values, failures, expected):
    ids = [row["query_id"] for row in values] + [row["query_id"] for row in failures]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("incomplete or duplicated query accounting")
    times = [row["elapsed_ms"] for row in values]
    return {
        "schema_version": 1,
        "dataset_id": name,
        "split": "test",
        "cutoff": 10,
        "includes_drafts": False,
        "configuration": config,
        "per_query": values,
        "failures": failures,
        "missing_queries": [],
        "results_sha256": digest(canonical(values)),
        "quality_complete": not failures,
        "metrics": {
            key: statistics.mean(row[key] for row in values) if values else None
            for key in ("ndcg", "recall", "mrr")
        },
        "latency_ms": {"p50": percentile(times, 0.5), "p95": percentile(times, 0.95)},
    }


def select_fusion(pipeline, queries, judgments, ids, protocol, defaults):
    configs = [
        dict(family=family, sparse_weight=weight, k=60)
        for family in ("weighted_rrf", "normalized_score")
        for weight in protocol["fusion_grid"][family]["sparse_weights"]
    ]
    values = [[] for _ in configs]
    for index, qid in enumerate(ids, 1):
        sparse, _ = pipeline.sparse(queries[qid], defaults)
        dense, _ = pipeline.dense(queries[qid])
        for config, metrics in zip(configs, values, strict=True):
            hits = fuse_variant(sparse, dense, config, pipeline.candidates)
            metrics.append(score(pipeline.documents(hits, qid), judgments[qid])["ndcg"])
        if index % 25 == 0:
            print(f"fusion development: {index}/{len(ids)}", flush=True)
    grid = [
        dict(configuration=config, ndcg=statistics.mean(metrics))
        for config, metrics in zip(configs, values, strict=True)
    ]
    chosen = {
        family: min(
            (row for row in grid if row["configuration"]["family"] == family),
            key=lambda row: (-row["ndcg"], row["configuration"]["sparse_weight"]),
        )["configuration"]
        for family in ("weighted_rrf", "normalized_score")
    }
    for row in grid:
        row["selected"] = row["configuration"] == chosen[row["configuration"]["family"]]
    return {
        "selected": chosen,
        "development_query_ids": ids,
        "grid_scores": grid,
        "selection_split": "SciFact development only",
    }


def prepare_controls(args, root, protocol, base, model):
    prepared, checked, data, queries = {}, {}, {}, {}
    for name in protocol["datasets"]:
        data[name] = args.baseline_work / "downloads" / name
        prepared[name] = json.loads((args.baseline_work / name / "prepared.json").read_bytes())
        if (
            prepared[name]["model"] != model.config
            or prepared[name]["protocol_sha256"] != digest(canonical(base))
            or prepared[name]["document_limit"] != 0
        ):
            raise ValueError(
                "baseline preparation must be complete and match the pinned model/protocol"
            )
        for filename, expected in prepared[name]["inputs"].items():
            if digest((data[name] / filename).read_bytes()) != expected:
                raise ValueError("baseline input checksum mismatch")
        queries[name] = {row["_id"]: row["text"] for row in rows(data[name] / "queries.jsonl")}
        checked[name] = {}
        for label in ("web_default", "importer_default"):
            control = protocol["chunk_controls"][label]
            settings = dict(
                base, chunk_token_budget=control["token_budget"], wordpiece_refinement=None
            )
            checked[name][label] = prepare(
                name,
                data[name],
                args.work / name / label,
                args.engine,
                model,
                settings,
                preflight_only=True,
                allow_overflow=True,
            )
            print(
                f"{name} {label}: {checked[name][label]['chunks']} chunks; "
                f"{checked[name][label].get('overflow_count', 0)} encoder overflows; no truncation",
                flush=True,
            )
    return prepared, checked, data, queries


def query_legs(pipeline, query, config, concurrent):
    started = time.perf_counter()
    (sparse, sparse_ms), (dense, dense_ms) = run_legs(
        lambda: pipeline.sparse(query, config), lambda: pipeline.dense(query), concurrent=concurrent
    )
    legs_ms = (time.perf_counter() - started) * 1000
    hits, fusion_ms = pipeline.hybrid(sparse, dense, config["rrf_k"])
    return dict(
        sparse=sparse,
        dense=dense,
        hits=hits,
        sparse_ms=sparse_ms,
        dense_ms=dense_ms,
        legs_ms=legs_ms,
        fusion_ms=fusion_ms,
        wall_ms=(time.perf_counter() - started) * 1000,
    )


def evaluate_legacy(
    pipeline, name, queries, judgments, ids, protocol, selection, defaults, work, reranker
):
    configurations = {
        "default_sparse": dict(defaults, timing="observed sequential leg"),
        "default_dense": dict(defaults, timing="observed sequential leg"),
        "default_hybrid": dict(defaults, scheduling="sequential", timing="wall clock"),
        "concurrent_hybrid": dict(defaults, scheduling="concurrent", timing="wall clock"),
        **{
            family: dict(config, timing="shared legs plus measured fusion")
            for family, config in selection["selected"].items()
        },
        "sparse_then_dense": dict(defaults, candidates=100, timing="wall clock"),
        "cross_encoder_top50": dict(reranker.config, timing="shared hybrid plus measured rerank"),
    }
    outcomes = {key: [] for key in configurations}
    failures = {key: [] for key in configurations}
    pipeline.sparse("retrieval", defaults)
    pipeline.dense("retrieval")
    reranker.score(
        "retrieval", [{"title": "Warmup", "text": "Retrieve evidence from research passages."}]
    )
    for number, qid in enumerate(ids, 1):
        checkpoint = work / "query-results" / (digest(qid.encode()) + ".json")
        if checkpoint.exists():
            current = json.loads(checkpoint.read_bytes())
        else:
            paths = {}
            for concurrent in (False, True) if number % 2 else (True, False):
                paths[concurrent] = query_legs(pipeline, queries[qid], defaults, concurrent)
            seq, parallel = paths[False], paths[True]
            if any(seq[field] != parallel[field] for field in ("sparse", "dense", "hits")):
                raise ValueError("sequential/concurrent ranking or score mismatch")
            current = {"rows": {}, "failures": {}}
            for label, hits, elapsed in (
                ("default_sparse", seq["sparse"], seq["sparse_ms"]),
                ("default_dense", seq["dense"], seq["dense_ms"]),
                ("default_hybrid", seq["hits"], seq["wall_ms"]),
                ("concurrent_hybrid", parallel["hits"], parallel["wall_ms"]),
            ):
                current["rows"][label] = measured_row(pipeline, qid, hits, elapsed, judgments)
            current["rows"]["concurrent_hybrid"].update(
                parity=True,
                leg_timings={
                    key: parallel[key] for key in ("sparse_ms", "dense_ms", "legs_ms", "fusion_ms")
                },
            )
            for family, config in selection["selected"].items():
                started = time.perf_counter()
                hits = fuse_variant(
                    parallel["sparse"], parallel["dense"], config, pipeline.candidates
                )
                duration = (time.perf_counter() - started) * 1000
                current["rows"][family] = measured_row(
                    pipeline,
                    qid,
                    hits,
                    parallel["legs_ms"] + duration,
                    judgments,
                    incremental_ms=duration,
                )
            hits, duration = pipeline.sparse_then_dense(queries[qid], defaults)
            current["rows"]["sparse_then_dense"] = measured_row(
                pipeline, qid, hits, duration, judgments
            )
            candidates = [
                dict(
                    chunk_id=hit["chunk_id"],
                    paper_id=pipeline.papers[hit["chunk_id"]],
                    title=pipeline.titles[pipeline.chunks[hit["chunk_id"]]["paper_version_id"]],
                    text=pipeline.chunks[hit["chunk_id"]]["text"],
                )
                for hit in parallel["hits"][:50]
            ]
            pool = freeze(
                work / "frozen-pools" / (digest(qid.encode()) + ".json"),
                dict(query_id=qid, query=queries[qid], candidates=candidates),
            )
            try:
                started = time.perf_counter()
                scores, diagnostics = reranker.score(queries[qid], candidates)
                ordered = sorted(
                    zip(candidates, scores, strict=True),
                    key=lambda row: (-row[1], row[0]["chunk_id"]),
                )
                hits = [
                    dict(chunk_id=row["chunk_id"], reranker_score=value) for row, value in ordered
                ] + parallel["hits"][50:]
                duration = (time.perf_counter() - started) * 1000
                current["rows"]["cross_encoder_top50"] = measured_row(
                    pipeline,
                    qid,
                    hits,
                    parallel["wall_ms"] + duration,
                    judgments,
                    incremental_ms=duration,
                    pool_sha256=digest(canonical(pool)),
                    candidate_ids=[row["chunk_id"] for row in candidates],
                    **diagnostics,
                )
            except (ValueError, RuntimeError) as error:
                current["failures"]["cross_encoder_top50"] = {
                    "query_id": qid,
                    "error": str(error),
                    "pool_sha256": digest(canonical(pool)),
                }
            save(checkpoint, current)
        for label in configurations:
            if label in current["rows"]:
                outcomes[label].append(current["rows"][label])
            else:
                failures[label].append(current["failures"][label])
        if number % 25 == 0 or number == len(ids):
            print(f"{name} frozen test: {number}/{len(ids)}", flush=True)
    return {
        label: report_run(name, config, outcomes[label], failures[label], ids)
        for label, config in configurations.items()
    }


def evaluate_sparse(control, name, queries, judgments, ids, config):
    control.sparse("retrieval", config)
    results = []
    for qid in ids:
        hits, elapsed = control.sparse(queries[qid], config)
        results.append(measured_row(control, qid, hits, elapsed, judgments))
    return report_run(
        name, dict(config, worker=control.startup, timing="wall clock"), results, [], ids
    )


def latency_comparison(left, right, samples, seed):
    a = {row["query_id"]: row["elapsed_ms"] for row in left["per_query"]}
    b = {row["query_id"]: row["elapsed_ms"] for row in right["per_query"]}
    if not a or set(a) != set(b):
        raise ValueError("latency comparison requires identical nonempty query sets")
    deltas = [b[key] - a[key] for key in sorted(a)]
    rng = random.Random(seed)
    draws = [statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(samples)]
    return {
        "paired_count": len(deltas),
        "mean_delta_ms_concurrent_minus_sequential": statistics.mean(deltas),
        "percentile_interval_95": [percentile(draws, 0.025), percentile(draws, 0.975)],
        "samples": samples,
        "seed": seed,
        "interpretation": "Query-paired warm wall-clock observations; alternating execution order.",
    }


def run(args, root):
    if (
        args.documents
        or args.embedding != "minilm"
        or args.work.resolve() == args.baseline_work.resolve()
    ):
        raise ValueError(
            "phase3 requires real models, full baseline documents, and a separate --work directory"
        )
    protocol = committed(root, args.protocol)
    base = committed(root, root / protocol["base_protocol"])
    original_selection = json.loads((args.baseline_work / "selection.json").read_bytes())
    if original_selection["protocol_sha256"] != digest(canonical(base)):
        raise ValueError("baseline selection protocol differs")
    source_paths = [
        *root.glob("python/src/retrievec/**/*.py"),
        *root.glob("engine/**/*.go"),
        root / "scripts/benchmark_beir.py",
    ]
    environment = {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "engine_sha256": digest(args.engine.read_bytes()),
        "source_sha256": {
            path.relative_to(root).as_posix(): digest(path.read_bytes())
            for path in sorted(source_paths)
        },
    }
    frozen_header = {
        "protocol_sha256": digest(canonical(protocol)),
        "base_selection_sha256": digest(canonical(original_selection)),
        "engine_sha256": environment["engine_sha256"],
        "source_sha256": environment["source_sha256"],
    }
    frozen_header["judgment_hashes"] = {
        str(path.relative_to(args.baseline_work)): digest(path.read_bytes())
        for name in protocol["datasets"]
        for path in sorted((args.baseline_work / "downloads" / name / "qrels").glob("*.tsv"))
    }
    environment["threads"] = {
        key: os.environ.get(key) for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")
    }
    freeze(args.work / "frozen-study.json", frozen_header)
    model = adapter("minilm")
    prepared, checked, data, queries = prepare_controls(args, root, protocol, base, model)
    save(args.work / "preflight-summary.json", checked)
    if args.phase in ("preflight", "prepare"):
        return
    train_path = data["scifact"] / "qrels/train.tsv"
    if digest(train_path.read_bytes()) != original_selection["train_qrels_sha256"]:
        raise ValueError("frozen development judgments changed")
    training = qrels(train_path)
    development_ids = order(list(training), protocol["seed"])[: len(training) // 2]
    if development_ids != original_selection["development_query_ids"] or set(training) & set(
        qrels(data["scifact"] / "qrels/test.tsv")
    ):
        raise ValueError("development split changed or overlaps test")
    selection_path = args.work / "fusion-selection.json"
    if selection_path.exists():
        selection = json.loads(selection_path.read_bytes())
    else:
        if args.phase == "evaluate":
            raise ValueError("freeze development selection with --phase tune first")
        pipeline = Pipeline(
            args.engine, args.baseline_work / "scifact", prepared["scifact"], model, 100
        )
        try:
            selection = select_fusion(
                pipeline, queries["scifact"], training, development_ids, protocol, base["defaults"]
            )
        finally:
            pipeline.close()
        freeze(selection_path, selection)
    if args.phase == "tune":
        return
    if selection["development_query_ids"] != development_ids:
        raise ValueError("fusion selection differs from frozen development split")
    freeze(args.work / "evaluation-selection.json", selection)
    reranker = CrossEncoder(protocol["reranker"])
    freeze(args.work / "reranker.json", reranker.config)
    result = {
        "schema_version": 2,
        "study": "phase3",
        "kind": "beir-smoke" if args.queries else "full-beir",
        "complete": False,
        "quality_evidence": False,
        "protocol": protocol,
        "protocol_sha256": frozen_header["protocol_sha256"],
        "environment": environment,
        "selection": selection,
        "baseline_selection": original_selection,
        "embedding": model.config,
        "reranker": reranker.config,
        "datasets": {},
        "defaults_changed": False,
    }
    if args.output.exists():
        previous = json.loads(args.output.read_bytes())
        if (
            previous.get("protocol_sha256") != result["protocol_sha256"]
            or previous.get("environment", {}).get("source_sha256") != environment["source_sha256"]
        ):
            raise ValueError("output belongs to another measurement; choose a new dated file")
    for name in protocol["datasets"]:
        judgments = qrels(data[name] / "qrels/test.tsv")
        ids = order(list(judgments), protocol["seed"])
        if args.queries:
            ids = ids[: args.queries]
        pipeline = Pipeline(args.engine, args.baseline_work / name, prepared[name], model, 100)
        try:
            reports = evaluate_legacy(
                pipeline,
                name,
                queries[name],
                judgments,
                ids,
                protocol,
                selection,
                base["defaults"],
                args.work / name,
                reranker,
            )
        finally:
            pipeline.close()
        for analyzer in protocol["document_controls"]["analyzers"]:
            label = "document_bm25_" + analyzer
            control = SparseControl(
                args.engine,
                args.work / name / label,
                documents=data[name] / "corpus.jsonl",
                analyzer=analyzer,
            )
            try:
                reports[label] = evaluate_sparse(
                    control, name, queries[name], judgments, ids, base["defaults"]
                )
            finally:
                control.close()
            print(f"{name}: completed {label}", flush=True)
        for label, metadata in checked[name].items():
            control = SparseControl(
                args.engine, args.work / name / (label + "-worker"), corpus=Path(metadata["corpus"])
            )
            try:
                reports[label + "_sparse"] = evaluate_sparse(
                    control, name, queries[name], judgments, ids, base["defaults"]
                )
            finally:
                control.close()
            if not metadata.get("overflow_count", 0):
                product = finish(args.work / name / label, args.engine, model, metadata)
                exact = Pipeline(args.engine, args.work / name / label, product, model, 100)
                try:
                    dense_rows, hybrid_rows = [], []
                    exact.dense("retrieval")
                    for qid in ids:
                        current = query_legs(exact, queries[name][qid], base["defaults"], True)
                        dense_rows.append(
                            measured_row(
                                exact, qid, current["dense"], current["dense_ms"], judgments
                            )
                        )
                        hybrid_rows.append(
                            measured_row(exact, qid, current["hits"], current["wall_ms"], judgments)
                        )
                    reports[label + "_dense"] = report_run(
                        name, base["defaults"], dense_rows, [], ids
                    )
                    reports[label + "_hybrid"] = report_run(
                        name, base["defaults"], hybrid_rows, [], ids
                    )
                finally:
                    exact.close()
        pairs = {
            "default_hybrid_vs_" + label: compare(
                reports["default_hybrid"],
                value,
                samples=protocol["bootstrap_samples"],
                seed=protocol["seed"],
            )
            for label, value in reports.items()
            if label not in ("default_hybrid", "default_sparse", "default_dense")
        }
        pairs["default_sparse_vs_document_bm25_unicode"] = compare(
            reports["default_sparse"],
            reports["document_bm25_unicode"],
            samples=protocol["bootstrap_samples"],
            seed=protocol["seed"],
        )
        for analyzer in protocol["document_controls"]["analyzers"][1:]:
            pairs["document_bm25_unicode_vs_" + analyzer] = compare(
                reports["document_bm25_unicode"],
                reports["document_bm25_" + analyzer],
                samples=protocol["bootstrap_samples"],
                seed=protocol["seed"],
            )
        result["datasets"][name] = {
            "query_count": len(ids),
            "qrels_sha256": digest((data[name] / "qrels/test.tsv").read_bytes()),
            "runs": reports,
            "paired_bootstrap": pairs,
            "paired_latency": latency_comparison(
                reports["default_hybrid"],
                reports["concurrent_hybrid"],
                protocol["bootstrap_samples"],
                protocol["seed"],
            ),
            "unavailable_configurations": {
                label + "_dense_and_hybrid": "Encoder limit exceeded; no truncation or refinement"
                for label, metadata in checked[name].items()
                if metadata.get("overflow_count", 0)
            },
            "prepared": prepared[name],
            "product_chunk_preflight": checked[name],
            "whole_paper_control": protocol["document_controls"]["whole_paper"],
        }
        save(args.output, result)
    result["complete"] = True
    result["quality_evidence"] = not args.queries and all(
        run["quality_complete"]
        for dataset in result["datasets"].values()
        for run in dataset["runs"].values()
    )
    save(args.output, result)
    print(args.output, flush=True)
