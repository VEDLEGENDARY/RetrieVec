"""Versioned questions and judgments with explicit human-review provenance."""

from pathlib import Path

from retrievallab.corpus.snapshot import canonical, digest, load_snapshot, parse_json


def load_dataset(path: Path, corpus: Path, *, require_reviewed: bool = False) -> dict:
    data = parse_json(path.read_bytes())
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported evaluation schema")
    identity = {key: value for key, value in data.items() if key != "dataset_id"}
    if data.get("dataset_id") != "ev_" + digest(canonical(identity)):
        raise ValueError("evaluation identity mismatch")
    manifest, _, chunks = load_snapshot(corpus)
    if data.get("corpus_snapshot_id") != manifest["snapshot_id"]:
        raise ValueError("evaluation corpus mismatch")
    valid_chunks = {chunk["chunk_id"] for chunk in chunks}
    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("empty evaluation queries")
    ids = set()
    for query in queries:
        if (
            not isinstance(query, dict)
            or not isinstance(query.get("query_id"), str)
            or not query["query_id"]
            or query["query_id"] in ids
        ):
            raise ValueError("invalid or duplicate query identity")
        ids.add(query["query_id"])
        if (
            query.get("split") not in ("development", "held_out")
            or query.get("mode") not in ("free_text", "structured")
            or not isinstance(query.get("query"), str)
            or not query["query"].strip()
        ):
            raise ValueError("invalid query or split")
    pairs = set()
    judgments = data.get("judgments")
    if not isinstance(judgments, list):
        raise ValueError("judgments must be a list")
    for judgment in judgments:
        pair = (judgment.get("query_id"), judgment.get("chunk_id"))
        if pair in pairs or pair[0] not in ids or pair[1] not in valid_chunks:
            raise ValueError("duplicate or unresolved judgment")
        pairs.add(pair)
        if (
            type(judgment.get("grade")) is not int
            or not 0 <= judgment["grade"] <= 3
            or not isinstance(judgment.get("rationale"), str)
            or not judgment["rationale"].strip()
        ):
            raise ValueError("invalid judgment grade or rationale")
        state = judgment.get("review_status")
        if state not in ("draft", "reviewed"):
            raise ValueError("invalid review state")
        if state == "reviewed" and (
            not isinstance(judgment.get("reviewer"), str) or not judgment["reviewer"].strip()
        ):
            raise ValueError("reviewed judgment requires reviewer")
        if state == "draft" and judgment.get("reviewer") is not None:
            raise ValueError("draft cannot claim a reviewer")
    if require_reviewed and (
        not judgments
        or any(j["review_status"] != "reviewed" for j in judgments)
        or {j["query_id"] for j in judgments} != ids
    ):
        raise ValueError("owner review incomplete")
    return data
