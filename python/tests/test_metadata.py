import tempfile
import unittest
from pathlib import Path

from retrievec.corpus.importer import import_manifest
from retrievec.corpus.metadata import PaperMetadata, parse_metadata
from retrievec.corpus.snapshot import CorpusError, canonical, digest, load_snapshot


class MetadataTests(unittest.TestCase):
    def test_enrichment_is_source_bound_and_preserves_plain_chunk_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b"A scientific finding."
            (root / "paper.txt").write_bytes(source)
            row = {
                "paper_id": "paper",
                "title": "Title",
                "authors": [],
                "path": "paper.txt",
                "source_sha256": digest(source),
                "source_url": None,
                "license_note": "Fixture",
            }
            manifest = root / "input.json"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": [row]}))
            metadata = parse_metadata(
                "doi",
                "10.1234/example",
                canonical(
                    {
                        "message": {
                            "DOI": "10.1234/example",
                            "title": ["Title"],
                            "published": {"date-parts": [[2020]]},
                        }
                    }
                ),
            )
            metadata["source_sha256"] = digest(source)
            plain = import_manifest(manifest, root, root / "corpora")
            enriched = import_manifest(
                manifest, root, root / "corpora", metadata_enrichment={"paper": metadata}
            )
            self.assertNotEqual(plain, enriched)
            corpus, papers, chunks = load_snapshot(enriched)
            self.assertEqual(chunks, load_snapshot(plain)[2])
            fields = PaperMetadata(root, corpus).attributes(papers[0])
            self.assertEqual(fields["year"], 2020)
            self.assertEqual(fields["metadata_provenance"]["source_sha256"], digest(source))
            self.assertEqual((root / "paper.txt").read_bytes(), source)
            metadata["source_sha256"] = "0" * 64
            with self.assertRaisesRegex(CorpusError, "does not match"):
                import_manifest(
                    manifest, root, root / "corpora", metadata_enrichment={"paper": metadata}
                )

    def test_crossref_fields_are_bound_to_raw_response_and_unknowns_stay_unknown(self):
        raw = canonical(
            {
                "message": {
                    "DOI": "10.1234/example",
                    "title": ["Title"],
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "published": {"date-parts": [[2020, 1]]},
                }
            }
        )
        value = parse_metadata("doi", "10.1234/EXAMPLE", raw)
        self.assertEqual(value["fields"]["authors"], ["Ada Lovelace"])
        self.assertEqual(value["fields"]["year"], 2020)
        self.assertEqual(value["field_provenance"]["title"]["response_sha256"], digest(raw))
        with self.assertRaisesRegex(ValueError, "different DOI"):
            parse_metadata("doi", "10.1234/other", raw)
        missing = parse_metadata(
            "doi",
            "10.1234/example",
            canonical({"message": {"DOI": "10.1234/example", "title": ["Title"]}}),
        )
        self.assertIsNone(missing["fields"]["year"])
        self.assertEqual(missing["fields"]["authors"], [])

    def test_arxiv_version_is_pinned_and_xml_entities_are_rejected(self):
        raw = (
            b'<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
            b"<id>http://arxiv.org/abs/2301.12345v2</id><title> A title </title>"
            b"<author><name>A. Author</name></author>"
            b"<published>2023-01-01T00:00:00Z</published></entry></feed>"
        )
        value = parse_metadata("arxiv", "2301.12345", raw)
        self.assertEqual(value["fields"]["arxiv_id"], "2301.12345v2")
        with self.assertRaisesRegex(ValueError, "different version"):
            parse_metadata("arxiv", "2301.12345v1", raw)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            parse_metadata("arxiv", "2301.12345", b"<!DOCTYPE feed><feed/>")
