"""Offline pinned cross-encoder sweep over saved, authorized hybrid candidate pools."""

import argparse
import hashlib
import json
from pathlib import Path

from retrievec.evaluation.files import validate_outputs, write_json
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
    try:
        validate_outputs([args.output], [args.input])
    except ValueError as error:
        parser.error(str(error))
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
        and all(
            not run["failures"]
            and run["paired_vs_plain_hybrid"]["metrics"]["ndcg"]["paired_count"]
            == len(data["pools"])
            for run in report["sizes"].values()
        ),
    )
    write_json(args.output, report)


if __name__ == "__main__":
    main()
