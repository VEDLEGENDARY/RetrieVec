"""Command-line tools for corpus import, validation, query capture and evaluation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from retrievec import __version__
from retrievec.client.capture import capture
from retrievec.client.http import Client, RetrievalError
from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import CorpusError, load_snapshot, parse_json
from retrievec.evaluation.report import evaluate


def main(argv: Sequence[str] | None = None) -> int:
    command_args = list(sys.argv[1:] if argv is None else argv)
    if command_args and command_args[0] == "registry":
        from retrievec.registry.cli import main as registry_main

        return registry_main(command_args[1:])
    parser = argparse.ArgumentParser(
        prog="retrievec",
        description="Import and validate corpora, capture retrieval runs, and evaluate results.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser("validate-snapshot", help="validate an on-disk corpus")
    validate.add_argument("directory", type=Path)
    ingest = subparsers.add_parser("import", help="import local text files and text-based PDFs")
    ingest.add_argument("--manifest", required=True, type=Path)
    ingest.add_argument("--source-root", required=True, type=Path)
    ingest.add_argument("--output", required=True, type=Path)
    ingest.add_argument("--collection", default="research")
    ingest.add_argument("--token-budget", type=int, default=256)
    ingest.add_argument(
        "--chunker", choices=("paragraph-v1", "paragraph-v2"), default="paragraph-v1"
    )
    ingest.add_argument("--overlap", type=int, default=0)
    ingest.add_argument("--engine", type=Path)
    ingest.add_argument("--metadata", type=Path, help="Source-bound paper metadata JSON")
    ingest.add_argument(
        "--section-aware", action="store_true", help="Opt in to explicit heading boundaries"
    )
    runner = subparsers.add_parser("run", help="capture query JSONL against the service")
    runner.add_argument("--url", default="http://127.0.0.1:8091")
    runner.add_argument("--queries", type=Path, required=True)
    runner.add_argument("--output", type=Path, required=True)
    evaluation = subparsers.add_parser("evaluate", help="recompute metrics from saved results")
    evaluation.add_argument("--run", type=Path, required=True)
    evaluation.add_argument("--dataset", type=Path, required=True)
    evaluation.add_argument("--corpus", type=Path, required=True)
    evaluation.add_argument("--split", choices=("development", "held_out"), default="development")
    evaluation.add_argument("--include-drafts", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "evaluate":
        try:
            evaluate(
                args.run,
                args.dataset,
                args.corpus,
                include_drafts=args.include_drafts,
                split=args.split,
            )
        except (ValueError, OSError, CorpusError) as error:
            parser.error(str(error))
        print(args.run / "report.md")
        return 0
    if args.command == "run":
        try:
            manifest = capture(Client(args.url), args.queries, args.output)
        except (ValueError, OSError, CorpusError, RetrievalError) as error:
            parser.error(str(error))
        print(manifest["ranking_sha256"])
        return 0
    if args.command == "import":
        try:
            target = import_manifest(
                args.manifest,
                args.source_root,
                args.output,
                args.collection,
                args.token_budget,
                GoAnalyzer(args.engine),
                section_aware=args.section_aware,
                chunker=args.chunker,
                overlap=args.overlap,
                metadata_enrichment=(
                    parse_json(args.metadata.read_bytes())["papers"] if args.metadata else None
                ),
            )
        except (CorpusError, OSError) as error:
            parser.error(str(error))
        print(target)
        return 0
    if args.command == "validate-snapshot":
        try:
            manifest, _, _ = load_snapshot(args.directory)
        except (CorpusError, OSError) as error:
            parser.error(str(error))
        print(manifest["snapshot_id"])
        return 0
    parser.print_help()
    return 0
