# Segment format v1

Unsigned integers use little endian; variable integers use canonical ULEB128.
The layout is exactly [96-byte header | chunk table | dictionary | postings |
32-byte SHA-256 footer], with no padding. The footer hashes all preceding bytes.
The manifest hashes the complete file. File magic remains RLSEG001.

| Header offset | Size | Value |
| --- | --- | --- |
| 0 | 8 | RLSEG001 |
| 8 | 2 | version 1 |
| 10 | 2 | flags 0 |
| 12 | 4 | header size 96 |
| 16 | 8 | complete file size |
| 24 | 8 | chunk count |
| 32 | 8 | term count |
| 40 | 8 | chunk offset 96 |
| 48 | 8 | dictionary offset |
| 56 | 8 | postings offset |
| 64 | 8 | footer offset |
| 72 | 8 | total token count |
| 80 | 16 | reserved zero |

Chunks, sorted by external ID bytes: ID byte length varint, UTF-8 ID, token length
varint. Terms, sorted by UTF-8 bytes: term length varint, term bytes, df varint,
absolute postings offset u64, postings byte length u64. Each posting is chunk gap,
tf, tf position gaps (varints). Initial ID/position is absolute zero; later gaps
are positive. Positions restart per chunk. Empty segments are invalid.

Readers validate checksums, exact boundaries, bounded lengths, canonical varints,
counts, order, positions and token totals before admission. They retain dictionary
and chunk metadata and use bounded ReadAt calls for requested postings. They do
not reconstruct the in-memory index from corpus text. Immutable files stay open
for pinned snapshots; this milestone performs no automatic garbage collection.
