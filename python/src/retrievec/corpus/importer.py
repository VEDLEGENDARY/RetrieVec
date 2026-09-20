"""Local extraction and deterministic paragraph packing."""

import bisect
import io
import re
from itertools import pairwise
from pathlib import Path

import pypdf

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.snapshot import (
    MAX_FILE_BYTES,
    CorpusError,
    digest,
    make_chunk,
    make_paper,
    parse_json,
    publish_snapshot,
)

SOURCE_FIELDS = {
    "paper_id",
    "title",
    "authors",
    "path",
    "source_url",
    "source_sha256",
    "license_note",
}


def extract_pages(
    path: Path, source: bytes, max_pages: int = 500
) -> tuple[str, list[tuple[int | None, str]]]:
    if path.suffix.lower() in (".txt", ".md"):
        try:
            return "utf8-text-v1", [(None, source.decode("utf-8", errors="strict"))]
        except UnicodeError as error:
            raise CorpusError(f"{path.name}: invalid UTF-8 text") from error
    if path.suffix.lower() != ".pdf":
        raise CorpusError(f"{path.name}: expected .txt, .md, or text-based .pdf")
    try:
        reader = pypdf.PdfReader(io.BytesIO(source), strict=True)
        if reader.is_encrypted:
            raise CorpusError(f"{path.name}: encrypted PDF is unsupported")
        if len(reader.pages) > max_pages:
            raise CorpusError(f"{path.name}: PDF exceeds {max_pages} pages")
        pages = [
            (number, page.extract_text(extraction_mode="plain") or "")
            for number, page in enumerate(reader.pages, 1)
        ]
        if sum(len(text.encode("utf-8")) for _, text in pages) > 10 * 1024 * 1024:
            raise CorpusError("PDF extracted text exceeds 10 MiB")
        return f"pypdf-{pypdf.__version__}-plain-v1", pages
    except CorpusError:
        raise
    except Exception as error:
        raise CorpusError(f"{path.name}: PDF extraction failed: {error}") from error


def chunk_page(text: str, tokens: list[dict], budget: int) -> list[str]:
    """Pack paragraphs where possible, retaining every original byte exactly once."""
    if type(budget) is not int or not 1 <= budget <= 4096:
        raise CorpusError("token budget must be between 1 and 4096")
    if not tokens:
        return []
    data = text.encode("utf-8")
    starts = [token["start"] for token in tokens]
    boundaries = [0, *(m.end() for m in re.finditer(rb"\r?\n[ \t]*\r?\n", data)), len(data)]
    pieces: list[tuple[bytes, int]] = []
    for start, end in pairwise(boundaries):
        first, last = bisect.bisect_left(starts, start), bisect.bisect_left(starts, end)
        cursor = start
        while last - first > budget:
            cut = starts[first + budget]
            pieces.append((data[cursor:cut], budget))
            cursor, first = cut, first + budget
        pieces.append((data[cursor:end], last - first))
    chunks: list[str] = []
    current = bytearray()
    count = 0
    for piece, size in pieces:
        if count and count + size > budget:
            chunks.append(current.decode("utf-8"))
            current, count = bytearray(), 0
        current.extend(piece)
        count += size
    if current:
        chunks.append(current.decode("utf-8"))
    return chunks


def import_manifest(
    manifest_path: Path,
    source_root: Path,
    output_root: Path,
    collection_id: str = "research",
    token_budget: int = 256,
    analyzer: GoAnalyzer | None = None,
    *,
    max_pages: int = 500,
) -> Path:
    if type(token_budget) is not int or not 1 <= token_budget <= 4096:
        raise CorpusError("token budget must be between 1 and 4096")
    manifest = parse_json(manifest_path.read_bytes())
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "sources"}
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or not isinstance(manifest["sources"], list)
        or not manifest["sources"]
    ):
        raise CorpusError("invalid source manifest schema")
    analyzer = analyzer or GoAnalyzer()
    analyzer.analyze([])
    chunker_version = f"paragraph-v1-{token_budget}-{analyzer.version}"
    papers, chunks = [], []
    source_root = source_root.resolve(strict=True)
    for record in manifest["sources"]:
        if not isinstance(record, dict) or set(record) != SOURCE_FIELDS:
            raise CorpusError("source record: missing or unexpected fields")
        if not isinstance(record["path"], str) or not record["path"]:
            raise CorpusError("source path must be nonempty text")
        if not isinstance(record["authors"], list):
            raise CorpusError("authors must be an array")
        path = (source_root / record["path"]).resolve(strict=True)
        if not path.is_relative_to(source_root) or not path.is_file():
            raise CorpusError("source path escapes the source root or is not a file")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise CorpusError(f"{path.name}: source exceeds 64 MiB")
        source = path.read_bytes()
        if digest(source) != record["source_sha256"]:
            raise CorpusError(f"{path.name}: source hash mismatch")
        extraction_version, pages = extract_pages(path, source, max_pages)
        paper = make_paper(
            paper_id=record["paper_id"],
            title=record["title"],
            authors=record["authors"],
            source=source,
            source_url=record["source_url"],
            extraction_version=extraction_version,
            license_note=record["license_note"],
        )
        papers.append(paper)
        ordinal = 0
        for page_number, text in pages:
            tokens = analyzer.analyze([text])[0]
            for chunk_text in chunk_page(text, tokens, token_budget):
                chunks.append(
                    make_chunk(
                        paper,
                        chunk_text,
                        ordinal,
                        collection_id,
                        chunker_version,
                        None if page_number is None else [page_number, page_number],
                    )
                )
                ordinal += 1
        if ordinal == 0:
            raise CorpusError(f"{path.name}: no indexable text; OCR is outside this milestone")
    return publish_snapshot(
        output_root,
        papers,
        chunks,
        collection_id,
        {
            "token_budget": token_budget,
            "analyzer_version": analyzer.version,
            "chunker_version": chunker_version,
            "overlap": 0,
        },
    )
