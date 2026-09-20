"""Run private-upload extraction in a disposable, time-bounded subprocess."""

import sys
from pathlib import Path

from retrievec.app.process_limits import limit_extraction
from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest


def main():
    limit_extraction()
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
    except Exception as error:
        # Original text and parser diagnostics must not enter worker logs.
        message = str(error)
        code = (
            "encrypted_pdf"
            if "encrypted PDF" in message
            else ("ocr_required" if "no indexable text" in message else "invalid_input")
        )
        print(code)
        raise SystemExit(2) from None
    print(corpus.name)


if __name__ == "__main__":
    main()
