"""Create a conservative final model/index decision from saved JSON artifacts."""

import argparse
import json
from pathlib import Path

from retrievec.corpus.snapshot import canonical
from retrievec.experiments.decision import compare_final_configs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--experimental", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    decision = compare_final_configs(
        load(args.reference), load(args.experimental), load(args.criteria)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(decision) + b"\n")
    print(decision["decision_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
