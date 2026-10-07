# Measurement records

The dated reports retain the measured observations, configurations, rejected
variants and limitations. Large JSON reports are stored as `.json.gz`; the
published tables and report reader support both plain and compressed JSON.
Compression changes packaging only, not metrics, provenance or review fields.

[archives-2026-10-06.json](archives-2026-10-06.json) records compressed and original
SHA-256 hashes and byte counts. Every archived file was decompressed and checked
against its original bytes before the uncompressed duplicate was removed.

Render an existing report without running models or changing measurements:

```sh
python scripts/render_beir_report.py docs/results/benchmark-2026-10-05-phase3.json.gz
```

For a newly measured, uniquely dated JSON file, pack it with:

```sh
python -m retrievec.evaluation.report_io docs/results/your-new-dated-report.json --remove-original
```

Packing refuses to overwrite an existing archive. The gzip timestamp is zero
for reproducible packaging. Existing benchmark commands still write plain JSON;
choose a new dated output rather than overwriting published observations.

The raw result archives remain in Git history. This reduces the current checkout
and removes the oversized individual file; it does not shrink historical clones
or rewrite published commits. No model weights, credentials or paper PDFs are
part of these records. Synthetic questions, automatic checks and human review
retain their original provenance labels.
