"""Compare two metrics.json reports without altering captured runs."""

import argparse
import json
from pathlib import Path

from retrievec.evaluation.paired import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    result = compare(
        json.loads(args.left.read_text(encoding="utf-8")),
        json.loads(args.right.read_text(encoding="utf-8")),
        samples=args.samples,
        seed=args.seed,
    )
    with args.output.open("x", encoding="utf-8") as file:
        file.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
