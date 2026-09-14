# Corpus snapshot v1

Each directory contains exactly the required manifest.json, papers.jsonl, and
chunks.jsonl files (additional files are not read). JSON uses sorted object keys,
ASCII escapes including surrogate pairs, compact separators, no NaN/Infinity,
and LF endings. Each record occupies one line. Duplicate keys are rejected.
Paper records sort by paper_version_id; chunk records sort by chunk_id.

Record fields are defined by PAPER_FIELDS and CHUNK_FIELDS in
python/src/retrievallab/corpus/snapshot.py. Unknown/missing fields and schema
versions are errors. Empty author arrays are allowed for unattributed sources.
Pages are null when unavailable, otherwise an inclusive positive [first,last] pair.
A snapshot has one collection and at least one paper and chunk. Multiple versions
of a logical paper may coexist; version IDs are unique. Each version's chunk
ordinals are contiguous from zero. IDs and hashes are always recomputed on load.

- Paper version: pv_ + SHA-256(canonical {paper_id,source_sha256}).
- Chunk: ch_ + SHA-256(canonical {paper_version_id,extraction_version,
  chunker_version,ordinal,text_sha256}). Text hashes cover exact UTF-8 text.
- Snapshot: ss_ + SHA-256(canonical manifest excluding snapshot_id).

The manifest contains schema_version, collection_id, files (SHA-256 per JSONL),
sources (paper identity, source URL/hash/license), extraction_versions,
chunker_versions, counts, configuration, and snapshot_id. Its file hashes cover
newlines. There are no timestamps. Configuration is a flat map of nonempty text
keys to nonempty strings, booleans, or signed 32-bit integers. Behavior-affecting
options must be included, and a changed chunker configuration receives a new
chunker version so differently prepared chunks cannot collide.

Publication writes to a sibling temporary directory, validates the complete
snapshot, then renames it to its content ID. An existing valid snapshot is reused;
corruption is an error. This provides validated visibility, not a claim of crash
durability. Files larger than 64 MiB and linked record files are rejected on load.

Rebuild synthetic golden records with `python scripts/build_fixture.py` after
installing the package. Twelve original synthetic documents are committed; real
paper full text and generated user snapshots belong under ignored artifacts/.
