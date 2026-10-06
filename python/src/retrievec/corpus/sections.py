"""Explicit heading boundaries and immutable passage provenance; no inferred sections."""

import re
from typing import Literal

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.registry.artifacts import identity
from retrievec.registry.worker import publish_bytes

Section = Literal[
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
    "unclassified",
]
SECTIONS = (
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
    "unclassified",
)
HEADINGS = {
    "abstract": "abstract",
    "introduction": "introduction",
    "background": "introduction",
    "methods": "methods",
    "materials and methods": "methods",
    "methodology": "methods",
    "results": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
}
HEADING = re.compile(r"^\s*(?:#{1,6}\s+)?(?:\d+(?:\.\d+)*[.)]?\s+)?([A-Za-z ]+):?\s*$")


def segments(text, previous="unclassified", raw_heading=None):
    """Return lossless page spans, recognizing only standalone known headings."""
    boundaries = []
    offset = 0
    for line in text.splitlines(keepends=True):
        match = HEADING.fullmatch(line.rstrip("\r\n"))
        label = HEADINGS.get(match[1].strip().casefold()) if match else None
        if label:
            position = offset
            if not boundaries and not any(c.isalpha() or c.isdecimal() for c in text[:offset]):
                position = 0  # Retain a punctuation/whitespace preamble in the first section.
            boundaries.append((position, label, line.strip()))
        offset += len(line)
    result = []
    start = 0
    for position, label, heading in boundaries:
        if position > start:
            result.append((start, position, previous, raw_heading))
        start, previous, raw_heading = position, label, heading
    if start < len(text):
        result.append((start, len(text), previous, raw_heading))
    return result, previous, raw_heading


def publish_provenance(root, mapping):
    value = {"schema_version": 1, "policy": "explicit-headings-v1", "chunks": mapping}
    key = "pp_" + digest(canonical(value))
    publish_bytes(root / "passage-provenance" / (key + ".json"), canonical(value) + b"\n")
    return key


class PassageProvenance:
    def __init__(self, root, corpus):
        self.mapping = {}
        key = corpus["configuration"].get("passage_provenance_id")
        if key is None:
            return
        path = root / "passage-provenance" / (identity(key, "pp_") + ".json")
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("invalid passage provenance path")
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("passage provenance exceeds size limit")
        value = parse_json(path.read_bytes())
        if "pp_" + digest(canonical(value)) != key or value["policy"] != "explicit-headings-v1":
            raise ValueError("passage provenance identity mismatch")
        self.mapping = value["chunks"]

    def attributes(self, chunk):
        row = self.mapping.get(chunk["chunk_id"])
        if row is None:
            return {"section": "unclassified", "section_heading": None, "text_offsets": None}
        if row["text_sha256"] != chunk["text_sha256"] or row["section"] not in SECTIONS:
            raise ValueError("passage provenance differs from retained text")
        return {key: row[key] for key in ("section", "section_heading", "text_offsets")}
