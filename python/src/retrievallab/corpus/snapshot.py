"""Version 1 corpus records, canonical identities, and validated publication."""

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 64 * 1024 * 1024
PAPER_FIELDS = {
    "schema_version",
    "paper_id",
    "paper_version_id",
    "title",
    "authors",
    "source_url",
    "source_sha256",
    "extraction_version",
    "license_note",
}
CHUNK_FIELDS = {
    "schema_version",
    "chunk_id",
    "paper_id",
    "paper_version_id",
    "collection_id",
    "ordinal",
    "text",
    "text_sha256",
    "chunker_version",
    "page_range",
}
MANIFEST_FIELDS = {
    "schema_version",
    "snapshot_id",
    "collection_id",
    "files",
    "sources",
    "extraction_versions",
    "chunker_versions",
    "counts",
    "configuration",
}


class CorpusError(ValueError):
    """A corpus violates the versioned record or snapshot contract."""


def canonical(value: Any) -> bytes:
    """Canonical JSON is ASCII, sorted by key, compact, and has no final newline."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CorpusError(f"{name}: expected nonempty text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise CorpusError(f"{name}: invalid Unicode") from error


def _hash(value: Any, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise CorpusError(f"{name}: expected lowercase SHA-256")


def _fields(record: Any, fields: set[str], name: str) -> None:
    if not isinstance(record, dict) or set(record) != fields:
        raise CorpusError(f"{name}: unexpected or missing fields")
    if type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA_VERSION:
        raise CorpusError(f"{name}: unknown schema version")


def paper_version_id(paper_id: str, source_sha256: str) -> str:
    return "pv_" + digest(canonical({"paper_id": paper_id, "source_sha256": source_sha256}))


def chunk_id(paper: dict, ordinal: int, text_sha256: str, chunker_version: str) -> str:
    return "ch_" + digest(
        canonical(
            {
                "paper_version_id": paper["paper_version_id"],
                "extraction_version": paper["extraction_version"],
                "chunker_version": chunker_version,
                "ordinal": ordinal,
                "text_sha256": text_sha256,
            }
        )
    )


def make_paper(
    *,
    paper_id: str,
    title: str,
    authors: list[str],
    source: bytes,
    source_url: str | None,
    extraction_version: str,
    license_note: str,
) -> dict:
    source_hash = digest(source)
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "paper_version_id": paper_version_id(paper_id, source_hash),
        "title": title,
        "authors": list(authors),
        "source_url": source_url,
        "source_sha256": source_hash,
        "extraction_version": extraction_version,
        "license_note": license_note,
    }


def make_chunk(
    paper: dict,
    text: str,
    ordinal: int,
    collection_id: str,
    chunker_version: str,
    page_range: list[int] | None = None,
) -> dict:
    text_hash = digest(text.encode("utf-8", errors="strict"))
    return {
        "schema_version": SCHEMA_VERSION,
        "chunk_id": chunk_id(paper, ordinal, text_hash, chunker_version),
        "paper_id": paper["paper_id"],
        "paper_version_id": paper["paper_version_id"],
        "collection_id": collection_id,
        "ordinal": ordinal,
        "text": text,
        "text_sha256": text_hash,
        "chunker_version": chunker_version,
        "page_range": page_range,
    }


def validate_records(papers: list[dict], chunks: list[dict], collection_id: str) -> None:
    _text(collection_id, "collection_id")
    if not papers or not chunks:
        raise CorpusError("snapshot must contain papers and chunks")
    versions: dict[str, dict] = {}
    for paper in papers:
        _fields(paper, PAPER_FIELDS, "paper")
        for name in ("paper_id", "title", "extraction_version", "license_note"):
            _text(paper[name], name)
        if not isinstance(paper["authors"], list):
            raise CorpusError("authors: expected array")
        for author in paper["authors"]:
            _text(author, "author")
        if paper["source_url"] is not None:
            _text(paper["source_url"], "source_url")
            if not paper["source_url"].startswith(("https://", "http://")):
                raise CorpusError("source_url: expected HTTP(S) URL or null")
        _hash(paper["source_sha256"], "source_sha256")
        expected = paper_version_id(paper["paper_id"], paper["source_sha256"])
        if paper["paper_version_id"] != expected:
            raise CorpusError("paper version ID mismatch")
        if expected in versions:
            raise CorpusError("duplicate paper version ID")
        versions[expected] = paper

    ids: set[str] = set()
    ordinals: dict[str, list[int]] = {version: [] for version in versions}
    for chunk in chunks:
        _fields(chunk, CHUNK_FIELDS, "chunk")
        for name in (
            "chunk_id",
            "paper_id",
            "paper_version_id",
            "collection_id",
            "text",
            "chunker_version",
        ):
            _text(chunk[name], name)
        if chunk["chunk_id"] in ids:
            raise CorpusError("duplicate chunk ID")
        ids.add(chunk["chunk_id"])
        paper = versions.get(chunk["paper_version_id"])
        if paper is None or paper["paper_id"] != chunk["paper_id"]:
            raise CorpusError("missing or inconsistent paper reference")
        if chunk["collection_id"] != collection_id:
            raise CorpusError("collection mismatch")
        if type(chunk["ordinal"]) is not int or not 0 <= chunk["ordinal"] <= 2**31 - 1:
            raise CorpusError("ordinal: expected nonnegative 32-bit integer")
        ordinals[chunk["paper_version_id"]].append(chunk["ordinal"])
        _hash(chunk["text_sha256"], "text_sha256")
        if digest(chunk["text"].encode("utf-8")) != chunk["text_sha256"]:
            raise CorpusError("text hash mismatch")
        expected = chunk_id(paper, chunk["ordinal"], chunk["text_sha256"], chunk["chunker_version"])
        if chunk["chunk_id"] != expected:
            raise CorpusError("chunk ID mismatch")
        pages = chunk["page_range"]
        if pages is not None and (
            not isinstance(pages, list)
            or len(pages) != 2
            or any(type(page) is not int for page in pages)
            or not 1 <= pages[0] <= pages[1] <= 2**31 - 1
        ):
            raise CorpusError("page_range: expected inclusive positive range or null")
    for values in ordinals.values():
        if not values or sorted(values) != list(range(len(values))):
            raise CorpusError("paper chunk ordinals must be contiguous from zero")


def _jsonl(records: list[dict], key: str) -> bytes:
    return b"".join(canonical(record) + b"\n" for record in sorted(records, key=lambda r: r[key]))


def encode_snapshot(
    papers: list[dict], chunks: list[dict], collection_id: str, configuration: dict
) -> tuple[dict, dict[str, bytes]]:
    validate_records(papers, chunks, collection_id)
    if not isinstance(configuration, dict):
        raise CorpusError("configuration: expected object")
    for key, value in configuration.items():
        _text(key, "configuration key")
        if type(value) not in (str, int, bool) or (
            type(value) is int and not -(2**31) <= value <= 2**31 - 1
        ):
            raise CorpusError("configuration values must be strings, booleans, or 32-bit integers")
        if isinstance(value, str):
            _text(value, "configuration value")
    files = {
        "papers.jsonl": _jsonl(papers, "paper_version_id"),
        "chunks.jsonl": _jsonl(chunks, "chunk_id"),
    }
    sources = [
        {
            key: paper[key]
            for key in (
                "paper_id",
                "paper_version_id",
                "source_url",
                "source_sha256",
                "license_note",
            )
        }
        for paper in sorted(papers, key=lambda p: p["paper_version_id"])
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "collection_id": collection_id,
        "files": {name: digest(data) for name, data in files.items()},
        "sources": sources,
        "extraction_versions": sorted({paper["extraction_version"] for paper in papers}),
        "chunker_versions": sorted({chunk["chunker_version"] for chunk in chunks}),
        "counts": {"papers": len(papers), "chunks": len(chunks)},
        "configuration": configuration,
    }
    manifest["snapshot_id"] = "ss_" + digest(canonical(manifest))
    files["manifest.json"] = canonical(manifest) + b"\n"
    return manifest, files


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CorpusError(f"invalid JSON constant: {value}")


def parse_json(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError) as error:
        raise CorpusError(f"invalid UTF-8 JSON: {error}") from error


def load_snapshot(directory: Path) -> tuple[dict, list[dict], list[dict]]:
    def read(name: str) -> bytes:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise CorpusError(f"{name}: missing, linked, or oversized file")
        return path.read_bytes()

    raw_manifest = read("manifest.json")
    manifest = parse_json(raw_manifest)
    _fields(manifest, MANIFEST_FIELDS, "manifest")
    paper_data, chunk_data = read("papers.jsonl"), read("chunks.jsonl")
    papers = [parse_json(line) for line in paper_data.splitlines()]
    chunks = [parse_json(line) for line in chunk_data.splitlines()]
    expected, files = encode_snapshot(
        papers, chunks, manifest["collection_id"], manifest["configuration"]
    )
    if manifest != expected:
        raise CorpusError("manifest identity, hashes, counts, or provenance mismatch")
    for name, actual in (
        ("manifest.json", raw_manifest),
        ("papers.jsonl", paper_data),
        ("chunks.jsonl", chunk_data),
    ):
        if files[name] != actual:
            raise CorpusError(f"{name}: noncanonical content or hash mismatch")
    return manifest, papers, chunks


def publish_snapshot(
    root: Path, papers: list[dict], chunks: list[dict], collection_id: str, configuration: dict
) -> Path:
    manifest, files = encode_snapshot(papers, chunks, collection_id, configuration)
    root.mkdir(parents=True, exist_ok=True)
    target = root / manifest["snapshot_id"]

    def verify_existing() -> None:
        if target.is_symlink() or load_snapshot(target)[0] != manifest:
            raise CorpusError("existing snapshot identity mismatch")

    if target.exists():
        verify_existing()
        return target
    stage = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=root))
    try:
        for name, data in files.items():
            (stage / name).write_bytes(data)
        load_snapshot(stage)
        try:
            stage.rename(target)
        except OSError:
            if not target.is_dir():
                raise
            verify_existing()
        return target
    finally:
        if stage.exists():
            shutil.rmtree(stage)
