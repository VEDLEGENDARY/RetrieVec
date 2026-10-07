"""Opt-in section-aware paragraph windows with bounded token overlap."""

import bisect
import re

from retrievec.corpus.snapshot import CorpusError

VERSION = "paragraph-v2"
HEADING = re.compile(r"^(?:#{1,6}\s+|(?:\d+(?:\.\d+)*\.?\s+))[A-Za-z][^\n]{1,100}$")
PARAGRAPH = re.compile(rb"\r?\n[ \t]*\r?\n")


def sections(text: str, current: str = "") -> tuple[list[tuple[str, str]], str]:
    """Split on explicit headings; carry a section title across PDF pages."""
    parts: list[tuple[str, str]] = []
    body: list[str] = []
    saw_heading = False
    for line in text.splitlines(keepends=True):
        candidate = line.strip()
        if HEADING.fullmatch(candidate):
            saw_heading = True
            if body:
                parts.append((current, "".join(body)))
                body = []
            current = candidate.lstrip("# ").strip()
        else:
            body.append(line)
    if body and "".join(body).strip():
        parts.append((current, "".join(body)))
    elif not parts and saw_heading:
        # A title-only record still needs an indexable passage.
        parts.append(("", current))
    return parts, current


def _windows(body: str, title: str, analyzer, budget: int, overlap: int) -> list[str]:
    data = body.encode("utf-8")
    tokens = analyzer.analyze([body])[0]
    if not tokens:
        return []
    prefix = f"Section: {title}\n\n" if title else ""
    overhead = len(analyzer.analyze([prefix])[0]) if prefix else 0
    capacity = budget - overhead
    if capacity <= overlap or capacity < 1:
        raise CorpusError("section title and overlap exceed paragraph-v2 token budget")
    starts = [token["start"] for token in tokens]
    paragraph_ends = [match.end() for match in PARAGRAPH.finditer(data)]
    chunks = []
    first = 0
    while first < len(tokens):
        last = min(first + capacity, len(tokens))
        if last < len(tokens):
            minimum = first + max(overlap + 1, capacity // 2)
            candidates = [
                bisect.bisect_left(starts, boundary)
                for boundary in paragraph_ends
                if starts[minimum] <= boundary <= starts[last]
            ]
            if candidates:
                last = min(last, max(candidates))
        start_byte = 0 if first == 0 else starts[first]
        end_byte = starts[last] if last < len(tokens) else len(data)
        passage = data[start_byte:end_byte].decode("utf-8")
        if passage.strip():
            chunks.append(prefix + passage)
        if last == len(tokens):
            break
        first = last - overlap
    return chunks


def chunk_page_v2(
    text: str, analyzer, budget: int, overlap: int, current_section: str = ""
) -> tuple[list[str], str]:
    if type(budget) is not int or not 1 <= budget <= 4096:
        raise CorpusError("paragraph-v2 token budget must be between 1 and 4096")
    if type(overlap) is not int or not 0 <= overlap < budget:
        raise CorpusError("paragraph-v2 overlap must be smaller than its token budget")
    found, current_section = sections(text, current_section)
    chunks = [
        chunk for title, body in found for chunk in _windows(body, title, analyzer, budget, overlap)
    ]
    return chunks, current_section
