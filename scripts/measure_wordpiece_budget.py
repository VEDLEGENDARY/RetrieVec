"""Measure retained chunks against the pinned MiniLM tokenizer, without truncation."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from huggingface_hub import hf_hub_download
from retrievec.corpus.snapshot import load_snapshot
from retrievec.dense.model import MODEL, REVISION
from tokenizers import Tokenizer


def measure(root):
    path = Path(hf_hub_download(MODEL, "tokenizer.json", revision=REVISION, local_files_only=True))
    tokenizer = Tokenizer.from_file(str(path))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    reports = []
    for directory in sorted(root.glob("ss_*")):
        manifest, _, chunks = load_snapshot(directory)
        lengths = sorted(len(tokenizer.encode(chunk["text"]).ids) for chunk in chunks)
        exceeded = sum(value > 256 for value in lengths)
        reports.append(
            {
                "snapshot": directory.name,
                "configuration": manifest["configuration"],
                "chunks": len(lengths),
                "overflow_count": exceeded,
                "overflow_rate": exceeded / len(lengths) if lengths else 0,
                "p50_wordpieces": statistics.median(lengths) if lengths else 0,
                "p95_wordpieces": lengths[max(0, (95 * len(lengths) + 99) // 100 - 1)]
                if lengths
                else 0,
                "max_wordpieces": max(lengths, default=0),
            }
        )
    if not reports:
        raise ValueError("No retained corpus snapshots found")
    return {
        "model": MODEL,
        "revision": REVISION,
        "tokenizer_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "limit_including_special_tokens": 256,
        "policy": "reject-v1",
        "corpora": reports,
        "note": "Retained local corpora only; not a general overflow estimate.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpora", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = measure(args.corpora)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
