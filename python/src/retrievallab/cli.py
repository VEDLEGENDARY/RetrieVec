"""Command-line entry point; corpus and evaluation commands arrive in later steps."""

import argparse
from collections.abc import Sequence

from retrievallab import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="retrievallab",
        description="Corpus and evaluation workspace. Workflow commands arrive in later steps.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
