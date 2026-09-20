"""Download the pinned CPU model and record a small real-inference smoke run."""

import argparse
import time
from pathlib import Path

from retrievec.corpus.snapshot import canonical
from retrievec.dense.model import MiniLM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    model = MiniLM()
    loaded = time.perf_counter()
    vectors = model.encode(["Dense retrieval compares semantic vectors.", "Stars form in clouds."])
    if vectors.shape != (2, 384):
        raise ValueError("unexpected embedding dimensions")
    rejected = False
    try:
        model.encode(["retrieval " * 300])
    except ValueError:
        rejected = True
    if not rejected:
        raise ValueError("oversized input was not rejected")
    result = {
        "configuration": model.config,
        "shape": list(vectors.shape),
        "load_seconds": loaded - start,
        "inference_seconds": time.perf_counter() - loaded,
        "oversized_input_rejected": rejected,
        "reviewed_quality_available": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result) + b"\n")
    print(args.output)


if __name__ == "__main__":
    main()
