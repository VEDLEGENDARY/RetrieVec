"""Evaluate authenticated product answers or export/import bound human reviews."""

import argparse
import asyncio
import json
from pathlib import Path

from retrievec.corpus.snapshot import load_snapshot
from retrievec.evaluation.answer_judge import judge_report
from retrievec.evaluation.answer_pipeline import evaluate
from retrievec.evaluation.answer_quality import export_review, import_review, summarize
from retrievec.registry.artifacts import Store


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument(
        "--dataset", type=Path, default=Path("datasets/answer_quality/questions-v1.json")
    )
    run.add_argument("--split", choices=["development", "validation", "test"], default="test")
    run.add_argument("--origin", required=True)
    run.add_argument(
        "--session", type=Path, required=True, help="Private cookie/CSRF JSON; never commit"
    )
    run.add_argument("--collection", required=True)
    run.add_argument("--snapshot", required=True)
    run.add_argument("--store", type=Path, required=True)
    run.add_argument("--providers", nargs="+", required=True, metavar="PROVIDER")
    run.add_argument("--timeout", type=int, default=360)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--resume", type=Path, help="Preserve recorded outcomes; run missing cases only"
    )
    export = commands.add_parser("export-review")
    export.add_argument("report", type=Path)
    export.add_argument("output", type=Path)
    review = commands.add_parser("import-review")
    review.add_argument("report", type=Path)
    review.add_argument("packet", type=Path)
    review.add_argument("output", type=Path)
    judge = commands.add_parser("judge")
    judge.add_argument("report", type=Path)
    judge.add_argument("--config", type=Path, required=True)
    judge.add_argument("--provider", required=True)
    judge.add_argument("--origin", required=True)
    judge.add_argument("--session", type=Path, required=True)
    judge.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        session = json.loads(args.session.read_text(encoding="utf-8"))
        store = Store(args.store)
        indexed = store.manifest(args.snapshot)
        corpus = load_snapshot(store.path("corpora", indexed["corpus_snapshot_id"], "ss_"))
        report = asyncio.run(
            evaluate(
                args,
                session,
                corpus,
                checkpoint=lambda value: write(args.output, value),
                resume=(
                    json.loads(args.resume.read_text(encoding="utf-8")) if args.resume else None
                ),
            )
        )
        write(args.output, report)
        return 0 if report["complete"] and report["all_runs_completed"] else 1
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if args.command == "judge":
        session = json.loads(args.session.read_text(encoding="utf-8"))
        write(args.output, asyncio.run(judge_report(report, args, session)))
    elif args.command == "export-review":
        write(args.output, export_review(report))
    else:
        import_review(report, json.loads(args.packet.read_text(encoding="utf-8")))
        write(args.output, summarize(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
