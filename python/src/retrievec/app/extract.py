"""Run private-upload extraction in a disposable, time-bounded subprocess."""

import os
import sys
from pathlib import Path

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest


def main():
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    manifest, store, collection, engine = sys.argv[1:]
    root = Path(store)
    try:
        corpus = import_manifest(
            Path(manifest),
            root / "sources",
            root / "corpora",
            collection,
            96,
            GoAnalyzer(Path(engine)),
            max_pages=100,
        )
    except Exception:
        # Original text and parser diagnostics must not enter worker logs.
        raise SystemExit(2) from None
    print(corpus.name)


if __name__ == "__main__":
    main()
