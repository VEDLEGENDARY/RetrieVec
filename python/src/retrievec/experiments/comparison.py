"""Frozen development selection and held-out three-way comparisons."""

from __future__ import annotations

from retrievec.corpus.snapshot import canonical, digest


def select_checkpoint(reports: list[dict], *, split: str = "development") -> dict:
    if split != "development" or not reports:
        raise ValueError("checkpoint selection requires development reports")
    candidates = []
    for report in reports:
        if report.get("split") != split or not report.get("checkpoint_id", "").startswith("ck_"):
            raise ValueError("invalid checkpoint selection report")
        ndcg = report.get("metrics", {}).get("ndcg", {}).get("mean")
        p95 = report.get("latency_ms", {}).get("p95")
        if ndcg is None or p95 is None:
            raise ValueError("selection metric is undefined")
        candidates.append((float(ndcg), -float(p95), -int(report["step"]), report))
    chosen = max(candidates)[3]
    identity = {
        "schema_version": 1,
        "split": split,
        "report_hashes": sorted(digest(canonical(report)) for report in reports),
        "selected_checkpoint_id": chosen["checkpoint_id"],
        "rule": "max_ndcg_then_min_p95_then_min_step-v1",
    }
    return dict(identity, selection_id="cs_" + digest(canonical(identity)))


def compare_three_way(
    no_reranker: dict,
    pretrained: dict,
    fine_tuned: dict,
    selection: dict,
    *,
    split: str = "held_out",
) -> dict:
    reports = {"no_reranker": no_reranker, "pretrained": pretrained, "fine_tuned": fine_tuned}
    hashes = [report.get("candidate_pool_hashes") for report in reports.values()]
    if split != "held_out" or any(report.get("split") != split for report in reports.values()):
        raise ValueError("final comparison requires held-out reports")
    if hashes[0] != hashes[1] or hashes[0] != hashes[2]:
        raise ValueError("three-way comparison requires identical candidate pools")
    if fine_tuned.get("checkpoint_id") != selection.get("selected_checkpoint_id"):
        raise ValueError("fine-tuned report does not use frozen checkpoint")
    return {
        "schema_version": 1,
        "split": split,
        "selection_id": selection["selection_id"],
        "candidate_pool_hashes": hashes[0],
        "systems": reports,
        "failures": {name: report.get("failures", []) for name, report in reports.items()},
        "comparison_id": "rc_" + digest(canonical({name: digest(canonical(report)) for name, report in reports.items()})),
    }
