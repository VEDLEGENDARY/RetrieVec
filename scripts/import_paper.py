"""Import an arXiv paper or associate an explicit local source with a DOI lookup."""

import argparse
from pathlib import Path
from urllib.parse import quote

import httpx
from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.metadata import bounded_get, resolve
from retrievec.corpus.snapshot import canonical, digest
from retrievec.registry.worker import publish_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    identifiers = parser.add_mutually_exclusive_group(required=True)
    identifiers.add_argument("--arxiv")
    identifiers.add_argument("--doi")
    parser.add_argument("--source", type=Path, help="Local PDF/text; required for DOI imports")
    parser.add_argument(
        "--work", type=Path, required=True, help="Retained original/metadata directory"
    )
    parser.add_argument("--output", type=Path, required=True, help="Corpus snapshot root")
    parser.add_argument("--collection", default="research")
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--section-aware", action="store_true")
    args = parser.parse_args()
    if args.doi and args.source is None:
        parser.error("DOI metadata does not guarantee an accessible full paper; supply --source")
    if args.source and (
        args.source.is_symlink() or args.source.suffix.lower() not in (".pdf", ".txt", ".md")
    ):
        parser.error("source must be a regular PDF, TXT, or Markdown file")
    kind, identifier = ("arxiv", args.arxiv) if args.arxiv else ("doi", args.doi)
    metadata, raw = resolve(kind, identifier)
    if args.source:
        if args.source.stat().st_size > 25 * 1024 * 1024:
            parser.error("source exceeds 25 MiB")
        original = args.source.read_bytes()
        suffix = args.source.suffix.lower()
        association = (
            "user-associated local source; identifier correspondence not independently verified"
        )
    else:
        url = "https://arxiv.org/pdf/" + metadata["fields"]["arxiv_id"]
        with httpx.Client(
            timeout=60, follow_redirects=False, headers={"User-Agent": "RetrieVec/0.1.0"}
        ) as client:
            original = bounded_get(client, url, 25 * 1024 * 1024)
        if not original.startswith(b"%PDF-"):
            raise ValueError("arXiv did not return a PDF")
        suffix = ".pdf"
        association = "downloaded from the resolved version's canonical arXiv PDF endpoint"
    source_hash = digest(original)
    metadata.update(source_sha256=source_hash, source_association=association)
    paper_id = kind + "-" + digest(identifier.encode())[:24]
    filename = source_hash + suffix
    publish_bytes(args.work / filename, original)
    publish_bytes(args.work / (metadata["response_sha256"] + ".metadata-response"), raw)
    record = {
        "paper_id": paper_id,
        "title": metadata["fields"]["title"],
        "authors": metadata["fields"]["authors"],
        "path": filename,
        "source_sha256": source_hash,
        "source_url": (
            "https://arxiv.org/abs/" + metadata["fields"]["arxiv_id"]
            if args.arxiv
            else "https://doi.org/" + quote(identifier, safe="/")
        ),
        "license_note": "Original terms apply; metadata does not confer redistribution rights.",
    }
    manifest = {"schema_version": 1, "sources": [record]}
    manifest_path = args.work / (digest(canonical(manifest)) + ".manifest.json")
    publish_bytes(manifest_path, canonical(manifest) + b"\n")
    metadata_path = args.work / (digest(canonical(metadata)) + ".metadata.json")
    publish_bytes(metadata_path, canonical({"papers": {paper_id: metadata}}) + b"\n")
    corpus = import_manifest(
        manifest_path,
        args.work,
        args.output,
        args.collection,
        analyzer=GoAnalyzer(args.engine),
        section_aware=args.section_aware,
        metadata_enrichment={paper_id: metadata},
    )
    print(corpus)
    print("Original retained in the work directory. Offline import creates no upload record.")


if __name__ == "__main__":
    main()
