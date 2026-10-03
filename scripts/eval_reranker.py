"""Offline pinned cross-encoder sweep over saved, authorized hybrid candidate pools."""

import argparse
import hashlib
import json
from pathlib import Path

from retrievec.experiments.reranker import (
    OnnxCrossEncoder,
    evaluate_pool_sweep,
    pretrained_config,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = json.loads(raw)
    if data.get("schema_version") != 1 or data.get("retrieval") != "hybrid":
        raise ValueError("input must contain versioned hybrid candidate pools")
    if data.get("scope") not in (
        "authorized_pinned_snapshot",
        "public_benchmark_pinned_snapshot",
    ) or not data.get("snapshot_id"):
        raise ValueError("candidate pools must carry authorized pinned-snapshot provenance")
    if data.get("judgment_provenance") not in ("human_reviewed", "beir_qrels"):
        raise ValueError("synthetic or pending judgments cannot establish quality")
    model = OnnxCrossEncoder(pretrained_config())
    report = evaluate_pool_sweep(
        data["pools"],
        data["judgments"],
        model,
        judgment_unit=data.get("judgment_unit", "chunk_id"),
    )
    report.update(
        input_sha256=hashlib.sha256(raw).hexdigest(),
        snapshot_id=data["snapshot_id"],
        judgment_provenance=data["judgment_provenance"],
        subset=data.get("subset", False),
        quality_evidence=not data.get("subset", False)
        and all(not run["failures"] for run in report["sizes"].values()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
