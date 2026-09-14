# Retrieval Lab: Advanced Document Evidence Handoff (Weeks 9–10)

## Required engineering workflow

Read and follow [ENGINEERING_WORKFLOW.md](ENGINEERING_WORKFLOW.md) in full before changing the repository. Its approval boundaries are part of this handoff.

- Work on only the first incomplete commit-sized step.
- Obtain approval for the proposed branch before creating or switching to it.
- Never implement or commit directly on `main`/`master`; integrate only through an approved pull request.
- After implementation and validation, present the diff, checks, limitations, and exact message; obtain approval before committing.
- Obtain separate authorization before pushing, opening/updating a pull request, merging, or starting the next step unless that exact action is already authorized.
- Use natural, project-focused branch names, commit messages, code, comments, documentation, and PR descriptions. Do not add tool attribution or fabricated authorship/review.
- Preserve unrelated changes and record actual evidence and incomplete gates honestly.
## Objective

Extend the initial release to scanned PDFs, tables, equations, and experimental chart evidence. This is a post-release milestone; extend its duration if quality gates require it. Read earlier plans and implementation status before editing.

Preserve original pages and distinguish extraction from interpretation. Every derived object must point to an actual source region. Unsupported or uncertain evidence stays visible as uncertain, not silently converted into authoritative claims.

## Extraction architecture

Add versioned Python extraction adapters behind the existing ingestion worker. Retain the original file and page render, extraction configuration/model revision, source hash, page number, bounding box, raw output, normalized output, and review status.

Coordinate contract: record page width/height, rotation, coordinate origin, units, and transformation to displayed page coordinates. Test rotated and cropped pages. Do not reuse text offsets as visual coordinates.

Evidence types: prose, table, equation, figure. Assign deterministic IDs from source/version, page/region, extractor/configuration, and content hash. Extraction changes create new corpus/retrieval snapshots; old citations continue resolving to their original retained evidence.

## Capabilities

| Type | Required behavior | Boundary |
|---|---|---|
| Scanned prose | Detect insufficient text layer, OCR bounded pages, reconstruct reading order | Mixed text/scanned pages handled individually; no double indexing |
| Tables | Preserve rows/columns, headers, caption, units, footnotes and source region | Merged cells and extraction ambiguity explicitly represented |
| Equations | Preserve crop, transcription, surrounding definitions and equation label | Valid syntax is not proof of mathematical equivalence |
| Charts | Preserve figure/caption and experimental structured observations | Never invent precise values from an unreadable plot |

Select current tools/models using official documentation, licenses, hardware smoke tests, and a small comparison set. Core text ingestion continues working without optional heavy dependencies. Run heavy extraction in bounded workers/cloud batch jobs only under configured data-processing consent.

## Structured evidence and retrieval

Store both source structure and a versioned searchable text representation. Table text must preserve header-value relationships and units; equation text retains local definitions; figure descriptions are labeled model-derived. Do not discard the original object after flattening it for retrieval.

Return evidence type and source locator with search hits. Initially reuse chunk-level search; add specialized ranking only if evaluated. Model-derived chart interpretations cannot become paper-reported numeric evidence without review.

The generation packet carries extraction/review status. Claims must distinguish reported values, OCR transcriptions, inferred observations, and missing values. A low-quality extraction should trigger page inspection or abstention.

## Quality dataset

Build a small licensed/owner-approved fixture set with text-only, scanned, mixed, multi-column, rotated, table-heavy, equation-heavy, and chart-heavy pages. Separate tuning and held-out pages by paper/source where practical. Request owner review in small batches.

Report prose character/word error, reading-order issues, table cell/header alignment and numeric/unit accuracy, equation transcription review, figure observation support, locator correctness, and end-to-end claim support. Automated text similarity is insufficient for table meaning or equation equivalence. Report counts by evidence type, failures, resource use, and unavailable capabilities.

## Fourteen commit-sized steps

| Step | Commit message | Deliverable and validation |
|---|---|---|
| 1 | `docs: define multimodal evidence and coordinate contracts` | Versioned types, page transforms, identity and migration ADR |
| 2 | `test: add reviewed document extraction fixtures` | Source permissions, category coverage, reviewed references/splits |
| 3 | `feat: classify page extraction requirements` | Text/scanned/mixed detection with measured errors |
| 4 | `feat: add bounded OCR worker adapter` | Versioned outputs, timeouts, optional dependency isolation |
| 5 | `feat: reconstruct page reading order and provenance` | Multi-column/rotation fixtures and no duplicate text layers |
| 6 | `feat: extract structured table evidence` | Cells/headers/units/captions with explicit ambiguity |
| 7 | `feat: add equation transcription evidence` | Original crops, context, labels and separate review status |
| 8 | `feat: add experimental figure evidence adapter` | Captions/regions and qualified observations without invented values |
| 9 | `feat: index typed evidence with snapshot versioning` | Searchable representations, stable old citations, new snapshots |
| 10 | `feat: inspect evidence regions in the research workspace` | Page overlays, structured view and original-source comparison |
| 11 | `feat: propagate extraction uncertainty into synthesis` | Evidence packet status, qualified claims and abstention cases |
| 12 | `test: evaluate extraction and grounded claim quality` | Reviewed per-type results, baseline comparison, known failures |
| 13 | `test: harden optional extraction resource handling` | Worker interruption, limits, consent, retries and unsupported states |
| 14 | `docs: deliver advanced evidence benchmark and handoff` | Reproducible report, model licenses, feature readiness matrix |

## Acceptance

Each enabled capability has source-region inspection, reviewed quality evidence, bounded execution, and snapshot-safe citations. Keep chart interpretation experimental if it does not pass support checks. Do not advertise universal PDF understanding. Record the exact enabled/experimental/unsupported matrix in `docs/reports/advanced-extraction.md` and implementation status.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
