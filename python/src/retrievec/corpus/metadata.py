"""Identifier lookups with bounded responses and field-level provenance."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.registry.artifacts import identity
from retrievec.registry.worker import publish_bytes

ARXIV = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?")
DOI = re.compile(r"10\.\d{4,9}/[^\s\x00-\x1f]{1,480}", re.I)
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def parse_metadata(kind, identifier, raw):
    if kind == "doi":
        value = json.loads(raw)["message"]
        if value["DOI"].casefold() != identifier.casefold():
            raise ValueError("Crossref returned a different DOI")
        title = value.get("title", [None])[0]
        authors = [
            " ".join(filter(None, (r.get("given"), r.get("family")))) or r.get("name")
            for r in value.get("author", [])
        ]
        date_key = "published" if "published" in value else "issued"
        date = value.get(date_key, {}).get("date-parts", [[]])
        year = date[0][0] if date and date[0] else None
        fields = {
            "title": title,
            "authors": [a for a in authors if a],
            "year": year,
            "doi": value["DOI"],
            "arxiv_id": None,
        }
        pointers = {
            "title": "message/title/0",
            "authors": "message/author",
            "year": f"message/{date_key}/date-parts/0/0",
            "doi": "message/DOI",
        }
        url = "https://api.crossref.org/works/" + quote(identifier, safe="")
    else:
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("unsafe metadata XML")
        entries = ET.fromstring(raw).findall(ATOM + "entry")
        if len(entries) != 1:
            raise ValueError("arXiv lookup must return exactly one paper")
        entry = entries[0]
        resolved = entry.findtext(ATOM + "id", "").split("/abs/")[-1]
        if not ARXIV.fullmatch(resolved) or re.sub(r"v\d+$", "", resolved) != re.sub(
            r"v\d+$", "", identifier
        ):
            raise ValueError("arXiv returned a different identifier")
        if re.search(r"v\d+$", identifier) and identifier != resolved:
            raise ValueError("arXiv returned a different version")
        published = entry.findtext(ATOM + "published")
        fields = {
            "title": " ".join(entry.findtext(ATOM + "title", "").split()),
            "authors": [a.findtext(ATOM + "name") for a in entry.findall(ATOM + "author")],
            "year": int(published[:4]) if published else None,
            "doi": entry.findtext(ARXIV_NS + "doi"),
            "arxiv_id": resolved,
        }
        pointers = {
            "title": "entry/title",
            "authors": "entry/author/name",
            "year": "entry/published",
            "doi": "entry/arxiv:doi",
            "arxiv_id": "entry/id",
        }
        url = "https://export.arxiv.org/api/query?id_list=" + quote(identifier, safe="")
    if not isinstance(fields["title"], str) or not fields["title"].strip():
        raise ValueError("metadata has no title")
    if fields["year"] is not None and (
        type(fields["year"]) is not int or not 1000 <= fields["year"] <= 9999
    ):
        raise ValueError("metadata has an invalid publication year")
    return {
        "schema_version": 1,
        "fields": fields,
        "provider": kind,
        "requested_identifier": identifier,
        "response_sha256": digest(raw),
        "response_url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "field_provenance": {
            key: {"path": path, "response_sha256": digest(raw)}
            for key, path in pointers.items()
            if fields[key] is not None
        },
    }


def bounded_get(client, url, limit):
    with client.stream("GET", url) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("unexpected redirect from identifier service")
        content = bytearray()
        for block in response.iter_bytes():
            content.extend(block)
            if len(content) > limit:
                raise ValueError("identifier response exceeds size limit")
    return bytes(content)


def resolve(kind, identifier, *, client=None):
    if kind not in ("doi", "arxiv"):
        raise ValueError("unknown identifier service")
    pattern = DOI if kind == "doi" else ARXIV
    if not isinstance(identifier, str) or not pattern.fullmatch(identifier):
        raise ValueError("invalid paper identifier")
    url = (
        "https://api.crossref.org/works/" + quote(identifier, safe="")
        if kind == "doi"
        else "https://export.arxiv.org/api/query?id_list=" + quote(identifier, safe="")
    )
    if client is None:
        with httpx.Client(
            timeout=30,
            follow_redirects=False,
            headers={"User-Agent": "RetrieVec/0.1.0 (https://github.com/VEDLEGENDARY/RetrieVec)"},
        ) as owned:
            return resolve(kind, identifier, client=owned)
    raw = bounded_get(client, url, 2 * 1024 * 1024)
    return parse_metadata(kind, identifier, raw), raw


def publish_metadata(root, records):
    value = {"schema_version": 1, "papers": records}
    key = "pm_" + digest(canonical(value))
    publish_bytes(root / "paper-metadata" / (key + ".json"), canonical(value) + b"\n")
    return key


class PaperMetadata:
    def __init__(self, root, corpus):
        self.records = {}
        key = corpus["configuration"].get("paper_metadata_id")
        if key is None:
            return
        path = root / "paper-metadata" / (identity(key, "pm_") + ".json")
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("invalid paper metadata path")
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("paper metadata exceeds size limit")
        value = parse_json(path.read_bytes())
        if "pm_" + digest(canonical(value)) != key or value["schema_version"] != 1:
            raise ValueError("paper metadata identity mismatch")
        self.records = value["papers"]

    def attributes(self, paper):
        record = self.records.get(paper["paper_id"])
        if record is None:
            return {"authors": paper["authors"], "year": None, "doi": None}
        if record["source_sha256"] != paper["source_sha256"]:
            raise ValueError("paper metadata belongs to a different source")
        fields = record["fields"]
        if fields["title"] != paper["title"] or fields["authors"] != paper["authors"]:
            raise ValueError("paper metadata differs from retained record")
        return {
            "authors": fields["authors"],
            "year": fields["year"],
            "doi": fields["doi"],
            "metadata_provenance": record,
        }
