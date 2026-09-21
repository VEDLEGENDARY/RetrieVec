"""Run private-upload extraction in a disposable, time-bounded subprocess."""

import sys
from pathlib import Path

from retrievec.app.process_limits import limit_extraction
from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import digest, parse_json


def main():
    limit_extraction()
    manifest, store, collection, engine, *options = sys.argv[1:]
    root = Path(store)
    try:
        configuration = {}
        if options:
            if len(options) != 1 or Path(options[0]).stat().st_size > 65536:
                raise ValueError("invalid extraction configuration")
            configuration = parse_json(Path(options[0]).read_bytes())
        bundles = dict(configuration.get("evidence_bundles", {}))
        if configuration.get("extraction_adapter"):
            from retrievec.extraction.adapters import AdapterConfig, extract_document

            adapter = AdapterConfig.model_validate(configuration["extraction_adapter"])
            for record in parse_json(Path(manifest).read_bytes())["sources"]:
                source = (root / "sources" / record["path"]).resolve()
                if not source.is_relative_to((root / "sources").resolve()):
                    raise ValueError("source path escapes store")
                if source.suffix.lower() != ".pdf":
                    continue
                if (
                    source.stat().st_size > 64 * 1024 * 1024
                    or digest(source.read_bytes()) != record["source_sha256"]
                ):
                    raise ValueError("source changed before extraction")
                bundles[record["source_sha256"]] = extract_document(source, root, adapter)
        corpus = import_manifest(
            Path(manifest),
            root / "sources",
            root / "corpora",
            collection,
            96,
            GoAnalyzer(Path(engine)),
            max_pages=100,
            evidence_bundles=bundles,
            evidence_root=root,
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
