"""Run bounded local workloads; credentials stay in an ignored session file."""

import argparse
import asyncio
import json

from retrievec.evaluation.load import PROFILES, execute
from retrievec.evaluation.resources import ResourceSampler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--session", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--provider", default="local")
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--requests", type=int)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--wall-seconds", type=float, default=900)
    parser.add_argument("--corpus-size", type=int, required=True)
    parser.add_argument("--configuration-note", default="")
    parser.add_argument("--allow-mutations", action="store_true")
    parser.add_argument("--slow-provider-confirmed", action="store_true")
    parser.add_argument("--server-pid", action="append", type=int, default=[])
    args = parser.parse_args()
    with ResourceSampler(args.server_pid) as resources:
        result = asyncio.run(execute(args))
    result["server_cpu_ram"] = resources.report()
    from pathlib import Path

    (Path(args.output) / "report.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["results"], indent=2))


if __name__ == "__main__":
    main()
