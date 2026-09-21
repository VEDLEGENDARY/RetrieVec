"""Sidecar mappings bind typed objects to unchanged version-1 corpus chunks."""

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.extraction.representation import REPRESENTATION_VERSION, numeric_text, searchable
from retrievec.extraction.store import EvidenceStore
from retrievec.registry.artifacts import identity
from retrievec.registry.worker import publish_bytes


def publish_map(root, mapping):
    value = {"schema_version": 1, "representation": REPRESENTATION_VERSION, "chunks": mapping}
    key = "ec_" + digest(canonical(value))
    publish_bytes(root / "evidence-maps" / (key + ".json"), canonical(value) + b"\n")
    return key


class EvidenceIndex:
    def __init__(self, root, corpus):
        self.store = EvidenceStore(root)
        self.mapping = {}
        key = corpus["configuration"].get("evidence_map_id")
        if key is not None:
            path = root / "evidence-maps" / (identity(key, "ec_") + ".json")
            if (
                path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve())
                or path.stat().st_size > 64 * 1024 * 1024
            ):
                raise ValueError("invalid evidence mapping path")
            value = parse_json(path.read_bytes())
            if "ec_" + digest(canonical(value)) != key or value["schema_version"] != 1:
                raise ValueError("evidence map identity mismatch")
            if value["representation"] != REPRESENTATION_VERSION:
                raise ValueError("unsupported evidence representation")
            self.mapping = value["chunks"]

    def object_for(self, chunk):
        row = self.mapping.get(chunk["chunk_id"])
        if row is None:
            return None
        if row["text_sha256"] != chunk["text_sha256"]:
            raise ValueError("evidence chunk text differs")
        evidence = self.store.read(row["evidence_id"])
        if evidence.source_sha256 != row["source_sha256"]:
            raise ValueError("evidence source differs")
        if chunk["page_range"] != [evidence.geometry.page, evidence.geometry.page]:
            raise ValueError("evidence page differs")
        if chunk["text"] not in searchable(evidence):
            raise ValueError("chunk is absent from evidence representation")
        return evidence

    def attributes(self, chunk):
        evidence = self.object_for(chunk)
        if evidence is None:
            return {"evidence_type": "prose", "source_locator": None}
        content = evidence.content.model_dump(mode="json")
        return {
            "evidence_type": evidence.content.kind,
            "source_locator": evidence.locator(),
            "evidence_object_id": evidence.identity,
            "structured_evidence": content,
            "extraction": {
                "extractor": evidence.extractor,
                "revision": evidence.revision,
                "derivation": evidence.derivation,
                "review": evidence.review.model_dump(),
                "confidence": evidence.confidence,
                "warnings": evidence.warnings,
                "synthesis_allowed": evidence.synthesis_allowed,
            },
            "numeric_support_text": numeric_text(evidence),
        }
