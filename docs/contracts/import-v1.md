# Local import and paragraph chunking v1

Use `retrievec import --manifest <json> --source-root <directory> --output <directory>`.
Options: --collection (research), --token-budget (256; range 1–4096), and --engine
(retrievald path, otherwise RETRIEVEC_ENGINE or PATH).

The source manifest is {"schema_version":1,"sources":[...]} with each source
containing paper_id, title, authors, path, source_url, source_sha256, and
license_note. Paths resolve inside source-root, and actual source bytes must match
the recorded SHA-256 before extraction. The command never downloads sources.

UTF-8 .txt/.md imports preserve text exactly and carry null page provenance.
Text PDFs use pinned pypdf plain extraction; pages have their actual one-based
PDF indices, not printed page labels. Encrypted PDFs, unsupported formats,
invalid UTF-8, and wholly unindexable sources fail. Sources are limited to 64 MiB
and PDFs to 500 pages. Image-only pages provide no extractable evidence; no OCR or
invented page locations are introduced. PDFs with omitted pages require inspection
before treating missing text as evidence of absence.

Each page is analyzed by Go. Blank lines delimit paragraphs; whole paragraphs pack
up to the token budget. Oversized paragraphs split at the next token's original
byte offset. Whitespace and punctuation remain attached to adjacent chunks. For
each indexable page, concatenating chunks in ordinal order reproduces its exact
extracted text. Chunks never cross a page boundary. There is no overlap.

Chunker identity includes behavior version, budget, and analyzer version. The
snapshot records these settings and extractor versions. A complete import is
validated before publication. Empty pages are omitted; wholly unindexable sources
cause the import to fail without publishing a partial corpus.

pypdf 6.18.1 is BSD-3-Clause and has no mandatory transitive dependencies on
Python 3.13. Its version is pinned in the project and development requirements.
Layout, tables, equations, headers, and reading order still need source review.
