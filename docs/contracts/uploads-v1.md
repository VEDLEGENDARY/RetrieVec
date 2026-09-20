# Private upload lifecycle

`POST /api/v1/collections/{id}/uploads` accepts multipart `files` with a unique
`Idempotency-Key`. A 202 means queued, not searchable. Poll the returned job ID;
only `succeeded` with `output_snapshot` confirms activation. Duplicate submission
keys return a conflict without creating another job. Uploads are serialized per
collection. New jobs contain the previously successful source set plus new files.

Defaults: 25 MiB/file, 10 files/request, 250 MiB retained originals/user, three
pending jobs/user, 100 PDF pages/file. The API generates storage keys and checks
PDF signatures. UTF-8/PDF parsing is in a disposable worker subprocess with a
120-second wall timeout. Linux also caps parser address space/CPU; Windows uses
the wall timeout and input/page/text bounds. OCR and encrypted PDFs are unsupported.

Start one consumer with `python -m retrievec.app.worker`; a database advisory
lock rejects a second consumer. Start Go in workspace principal mode (`*`).
Model download should be completed before accepting real hybrid uploads. The
normal embedding model is MiniLM; `fixture` is explicitly synthetic test plumbing.

Failed originals still count toward storage usage. Archive hides retained content
and cancels work; it is not physical erasure. An operator must perform any purge.
Legacy CLI snapshots without upload provenance cannot be appended in the browser;
import those originals into a new private collection. No silent replacement.
