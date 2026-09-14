# Seed import inspection

Scope: local extraction and chunk correctness; no retrieval-quality claims.

Snapshot: `ss_b135c1917acedc77650e0e21f5fff9fd58e28d36f460f4d392125c3f50048d8d`.
Environment: Windows amd64, Python 3.13.15, pypdf 6.18.1, Go 1.26.8,
analyzer-v1-unicode-15.0.0. Budget: 256 tokens, zero overlap, page-local chunks.

| Source | Pages | Chunks | Tokens |
| --- | ---: | ---: | ---: |
| [Dense Passage Retrieval](https://aclanthology.org/2020.emnlp-main.550/) | 13 | 42 | 9397 |
| [COIL](https://aclanthology.org/2021.naacl-main.241/) | 13 | 34 | 7326 |
| [Entity-centric questions](https://aclanthology.org/2021.emnlp-main.496/) | 11 | 34 | 7064 |
| [Hindi-BEIR](https://aclanthology.org/2025.naacl-long.220/) | 21 | 52 | 10780 |
| [BEIR-NL](https://aclanthology.org/2025.bucc-1.5/) | 10 | 31 | 7065 |

All 193 chunks have 1–256 tokens and actual PDF page indices. No pages were skipped.
The audit reconstructed every extracted page exactly from its ordered chunks,
checking for gaps and overlap. Two repeated CLI imports produced the same snapshot.
The source hashes, titles, and authors are pinned in datasets/manifests/seed-papers-v1.json.

Rendered title pages from all five PDFs were visually inspected. The downloaded
PDFs are authoritative where bibliographic metadata differs (DPR author diacritics
and BEIR-NL author order). These are multi-column documents; the entity-retrieval
paper also places a results table on its first page. Plain extraction retains
layout artifacts, line-break hyphenation, headers, footers, and table text. Token
budgets may split sentences. Exact text preservation does not imply faithful
table structure or reading order. Full page-by-page visual review is not claimed.

## Source access

ACL's [data-access FAQ](https://aclanthology.org/faq/) documents direct PDF access.
The robots.txt endpoint returned 404 at acquisition; no robots restrictions were
published there. Five known paper URLs were fetched sequentially with three-second
spacing, without crawling. These ACL materials are covered by the post-2016
[CC BY 4.0 copyright policy](https://aclanthology.org/faq/copyright/).
Only metadata and hashes are committed. PDFs, extracted full text, snapshots, and
inspection images stay under ignored artifacts/.

## Reproduce

Install the pinned requirements and run scripts/check.py. Obtain the five source
PDFs from the manifest's landing pages and place them under artifacts/papers with
the listed filenames. A changed download is rejected by its SHA-256 pin.

```powershell
$env:RETRIEVALLAB_ENGINE = (Resolve-Path artifacts/bin/retrievald.exe).Path
.\.venv\Scripts\python.exe -m retrievallab import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/seed-snapshots
.\.venv\Scripts\python.exe scripts/audit_import.py artifacts/seed-snapshots/ss_b135c1917acedc77650e0e21f5fff9fd58e28d36f460f4d392125c3f50048d8d --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers
```

Use .venv/bin/python and the corresponding engine path on Linux. CI uses original
synthetic source fixtures and dynamically constructed test PDFs, without downloads.
