"""Describe retained extraction records without guessing OCR from file types."""


def extraction_provenance(root, papers):
    result = {}
    for paper in papers:
        version = paper["extraction_version"]
        record = {
            "source_sha256": paper["source_sha256"],
            "extraction_version": version,
            "extractors": [],
            "ocr_used": None,
            "derivations": [],
        }
        if version == "utf8-text-v1":
            record.update(
                extractors=[{"name": "UTF-8 text reader", "revision": "v1"}],
                ocr_used=False,
                derivations=["source_text"],
            )
        elif version.startswith("pypdf-") and version.endswith("-plain-v1"):
            record.update(
                extractors=[{"name": "pypdf", "revision": version[6:-9]}],
                ocr_used=False,
                derivations=["source_text"],
            )
        elif version.startswith("typed-evidence-v1-"):
            from retrievec.extraction.store import EvidenceStore

            bundle, objects = EvidenceStore(root).bundle(version.removeprefix("typed-evidence-v1-"))
            if bundle["source_sha256"] != paper["source_sha256"]:
                raise ValueError("extraction provenance source differs")
            extractors = sorted({(item.extractor, item.revision) for item in objects})
            derivations = sorted({item.derivation for item in objects})
            record.update(
                extractors=[{"name": name, "revision": revision} for name, revision in extractors],
                ocr_used="ocr" in derivations,
                derivations=derivations,
            )
        result[paper["source_sha256"]] = record
    return result
