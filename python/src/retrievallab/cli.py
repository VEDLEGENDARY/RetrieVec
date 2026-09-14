"""Command-line entry point; corpus and evaluation commands arrive in later steps."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from retrievallab import __version__
from retrievallab.corpus.snapshot import CorpusError, load_snapshot


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="retrievallab",
        description="Corpus and evaluation workspace. Workflow commands arrive in later steps.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser("validate-snapshot", help="validate an on-disk corpus")
    validate.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    if args.command == "validate-snapshot":
        try:
            manifest, _, _ = load_snapshot(args.directory)
        except (CorpusError, OSError) as error:
            parser.error(str(error))
        print(manifest["snapshot_id"])
        return 0
    parser.print_help()
    return 0
