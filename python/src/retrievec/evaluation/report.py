"""Compute reports from captured results with verified input hashes."""

from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.evaluation.dataset import load_dataset
from retrievec.evaluation.metrics import aggregate, metrics


def evaluate(
    run: Path,
    dataset_path: Path,
    corpus: Path,
    *,
    include_drafts: bool = False,
    split: str = "development",
    k: int = 10,
) -> dict:
    if split not in ("development", "held_out"):
        raise ValueError("invalid split")
    dataset = load_dataset(dataset_path, corpus)
    manifest = parse_json((run / "manifest.json").read_bytes())
    raw = (run / "results.jsonl").read_bytes()
    if digest(raw) != manifest["results_sha256"]:
        raise ValueError("run result checksum mismatch")
    service = manifest["service"]
    if (
        service.get("corpus_snapshot_id", service.get("snapshot_id"))
        != dataset["corpus_snapshot_id"]
    ):
        raise ValueError("run and evaluation corpus differ")
    queries = {q["query_id"]: q for q in dataset["queries"] if q["split"] == split}
    rows, failures, seen = [], [], set()
    for line in raw.splitlines():
        result = parse_json(line)
        key = result["query_id"]
        if key in seen:
            raise ValueError("duplicate query result")
        seen.add(key)
        if key not in queries:
            continue
        if (
            result["request"]["query"] != queries[key]["query"]
            or result["request"]["mode"] != queries[key]["mode"]
        ):
            raise ValueError("query content differs from dataset")
        if "error" in result:
            failures.append({"query_id": key, "error": result["error"]})
            continue
        judgments = {
            j["chunk_id"]: j["grade"]
            for j in dataset["judgments"]
            if j["query_id"] == key and (include_drafts or j["review_status"] == "reviewed")
        }
        rows.append(
            {
                "query_id": key,
                **metrics([hit["chunk_id"] for hit in result["response"]["hits"]], judgments, k),
            }
        )
    output = {
        "schema_version": 1,
        "dataset_id": dataset["dataset_id"],
        "results_sha256": digest(raw),
        "split": split,
        "cutoff": k,
        "includes_drafts": include_drafts,
        "conventions": (
            "Unjudged gains use zero only for metric arithmetic; no-positive metrics "
            "are null and excluded from means. Failures are separate from empty "
            "results."
        ),
        "per_query": rows,
        "aggregate": aggregate(rows),
        "failures": failures,
        "missing_queries": sorted(set(queries) - seen),
    }
    (run / "metrics.json").write_bytes(canonical(output) + b"\n")
    text = [
        "# Retrieval evaluation",
        "",
        f"Dataset: {dataset['dataset_id']}",
        f"Split: {split}. Draft judgments included: {include_drafts}.",
        "",
        output["conventions"],
        "",
        "| Metric | Mean | Defined queries |",
        "| --- | --- | --- |",
    ]
    for key in ("ndcg", "mrr", "recall", "coverage"):
        value = output["aggregate"][key]
        text.append(f"| {key}@{k} | {value['mean']} | {value['defined_queries']} |")
    text.extend(
        [
            "",
            f"Failures: {len(failures)}. Missing queries: {len(output['missing_queries'])}.",
            "Synthetic or draft results are plumbing evidence, not real-corpus quality evidence.",
        ]
    )
    (run / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return output
