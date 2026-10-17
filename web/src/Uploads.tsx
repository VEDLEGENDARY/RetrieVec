import { stateLabel } from "./presentation";
import {
  Button,
  IconButton,
  Field,
  Input,
  Disclosure,
  StatusBadge,
  Surface,
  Notice,
} from "./ui";
import { useEffect, useRef, useState } from "react";
import { api, type Collection, type Job, type Session } from "./api";
import { FileText, UploadCloud, X, CheckCircle2 } from "lucide-react";
import { UploadProgress } from "./features/uploads/UploadProgress";
import "./features/uploads/uploads.css";

function fileProblem(file: File) {
  if (!/\.(pdf|txt|md)$/i.test(file.name))
    return "Use a PDF, text, or Markdown file.";
  if (file.size === 0)
    return "This file is empty. Choose a file containing text.";
  if (file.size > 25 * 1024 * 1024)
    return "This file exceeds 25 MiB. Split it into smaller files.";
  return null;
}
function fileSize(bytes: number) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KiB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

const stages: Record<string, string> = {
  queued: "Waiting for the worker",
  extract: "Extracting document text",
  chunk: "Preparing passages",
  embed: "Encoding passages",
  sparse_build: "Building the search index",
  validate: "Checking snapshot artifacts",
  activate: "Activating the searchable snapshot",
};
const failures: Record<string, string> = {
  invalid_input:
    "Could not extract usable text. Use unencrypted, text-based PDFs (100 pages maximum) or UTF-8 text.",
  unavailable:
    "A service is unavailable. Transient failures retry automatically.",
  stale_parent:
    "The collection changed during processing. Select the files and submit again.",
  attempts_exhausted:
    "Automatic retries were exhausted. Check the worker, then submit the files again.",
  extraction_timeout:
    "Text extraction exceeded its time limit. Try a smaller document.",
  encrypted_pdf: "This PDF is encrypted. Upload an unencrypted copy.",
  ocr_required:
    "No readable text was found. This upload path requires a PDF with readable text. Apply OCR before uploading, or ask the operator about configured advanced extraction.",
};

export function Uploads({
  collection,
  session,
  refresh,
  fail,
  onSearch,
}: {
  collection: Collection;
  session: Session;
  refresh: () => Promise<void>;
  fail: (error: unknown) => void;
  onSearch: () => void;
}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [removedFile, setRemovedFile] = useState<{
    file: File;
    index: number;
  } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [unconfirmed, setUnconfirmed] = useState(false),
    [jobsRefresh, setJobsRefresh] = useState(0);
  const form = useRef<HTMLFormElement>(null);
  const requestKey = useRef(crypto.randomUUID());
  const input = useRef<HTMLInputElement>(null);
  const observed = useRef(new Set<string>());
  useEffect(() => {
    if (!collection.can_manage) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const values = await api<Job[]>(
          `/api/v1/collections/${collection.collection_id}/jobs`,
          { signal: controller.signal },
        );
        if (!live) return;
        setJobs(values);
        const completed = values.filter(
          (job) =>
            job.state === "succeeded" && !observed.current.has(job.job_id),
        );
        values.forEach((job) => {
          if (job.state === "succeeded") observed.current.add(job.job_id);
        });
        if (completed.length) await refresh();
      } catch (error) {
        if (live) fail(error);
      } finally {
        if (live) timer = setTimeout(poll, 2500);
      }
    }
    void poll();
    return () => {
      live = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [
    collection.collection_id,
    collection.can_manage,
    refresh,
    fail,
    jobsRefresh,
  ]);
  async function submit(event: React.SubmitEvent) {
    event.preventDefault();
    if (!files.length) return;
    if (files.length > 10 || files.some((file) => fileProblem(file))) {
      setNotice("Choose up to 10 files, no larger than 25 MiB each.");
      return;
    }
    setSending(true);
    setUnconfirmed(false);
    setNotice("Sending original files…");
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    try {
      const job = await api<Job>(
        `/api/v1/collections/${collection.collection_id}/uploads`,
        {
          method: "POST",
          body,
          headers: { "Idempotency-Key": requestKey.current },
        },
        session.csrf_token,
      );
      setJobs((current) => [
        job,
        ...current.filter((item) => item.job_id !== job.job_id),
      ]);
      setNotice(
        "Upload received. Preparing your papers for search; you can follow progress below.",
      );
      if (input.current) input.current.value = "";
      setFiles([]);
      setRemovedFile(null);
      requestKey.current = crypto.randomUUID();
    } catch (error) {
      setUnconfirmed(true);
      fail(error);
      setNotice(
        "Upload was not confirmed. Refresh job status before resubmitting.",
      );
    } finally {
      setSending(false);
    }
  }
  if (!collection.can_manage)
    return (
      <p className="muted">This curated collection is managed by its owner.</p>
    );
  const pending = jobs.some((job) =>
    ["queued", "running", "retry_wait"].includes(job.state),
  );
  function addFiles(selected: File[]) {
    if (!selected.length || sending || pending) return;
    if (files.length + selected.length > 10) {
      setNotice(
        "Choose up to 10 files per batch. Remove files before adding more.",
      );
      return;
    }
    setFiles((current) => [...current, ...selected]);
    requestKey.current = crypto.randomUUID();
    setUnconfirmed(false);
    setNotice("");
  }
  return (
    <Surface className="uploads" aria-labelledby="upload-heading">
      <div>
        <h2 id="upload-heading">Add to your sources</h2>
        <p>
          Add research papers and notes to your collection. PDF, text or
          Markdown; up to 10 files, 25 MiB each, and 100 pages per PDF.
        </p>
      </div>
      <form ref={form} className="upload-composer" onSubmit={submit}>
        <div
          className={dragging ? "upload-dropzone dragging" : "upload-dropzone"}
          onDragOver={(event) => {
            event.preventDefault();
            if (!sending && !pending) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            addFiles(Array.from(event.dataTransfer.files));
          }}
        >
          <UploadCloud size={32} aria-hidden="true" />
          <h3>Drop your papers here</h3>
          <p>Or choose files, review your selection, and upload when ready.</p>
          <Field
            label="Choose documents"
            description="PDF with readable text, text, or Markdown. Up to 10 files; 25 MiB per file."
            error={
              files.some((file) => fileProblem(file))
                ? "Some selected files cannot be uploaded. Remove or replace the files marked below."
                : undefined
            }
          >
            <Input
              id="documents"
              ref={input}
              type="file"
              accept=".pdf,.txt,.md"
              multiple
              disabled={sending || pending}
              onChange={(event) => {
                addFiles(Array.from(event.target.files ?? []));
                event.target.value = "";
              }}
            />
          </Field>
        </div>
        {files.length > 0 && (
          <div className="upload-queue">
            <div className="queue-heading">
              <h3>Ready for review</h3>
              <span>
                {files.length}/10 files ·{" "}
                {fileSize(files.reduce((sum, file) => sum + file.size, 0))}
              </span>
            </div>
            <ul>
              {files.map((file, index) => (
                <li key={`${file.name}-${index}`}>
                  <FileText size={19} aria-hidden="true" />
                  <div>
                    <strong>{file.name}</strong>
                    <small>
                      <span className="metric">{fileSize(file.size)}</span> ·{" "}
                      {file.type ||
                        `.${file.name.split(".").at(-1)?.toLowerCase() ?? "unknown"}`}
                    </small>
                    <small className={fileProblem(file) ? "file-error" : ""}>
                      {fileProblem(file) ?? "Passes local file checks"}
                    </small>
                  </div>
                  <IconButton
                    type="button"
                    disabled={sending}
                    aria-label={`Remove ${file.name}`}
                    onClick={() => {
                      setRemovedFile({ file, index });
                      setFiles((current) =>
                        current.filter((_, position) => position !== index),
                      );
                      requestKey.current = crypto.randomUUID();
                      setUnconfirmed(false);
                    }}
                  >
                    <X size={17} aria-hidden="true" />
                  </IconButton>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="upload-actions">
          <span>
            <CheckCircle2 size={16} aria-hidden="true" /> Files stay in your
            private collection.
          </span>
          <Button
            className="primary"
            loading={sending}
            type="submit"
            disabled={
              sending ||
              pending ||
              !files.length ||
              files.some((file) => Boolean(fileProblem(file)))
            }
          >
            {sending
              ? "Sending…"
              : pending
                ? "Processing current upload…"
                : "Upload documents"}
          </Button>
        </div>
      </form>
      {removedFile && (
        <Button
          disabled={sending || pending || files.length >= 10}
          onClick={() => {
            setFiles((current) => {
              const next = [...current];
              next.splice(
                Math.min(removedFile.index, next.length),
                0,
                removedFile.file,
              );
              return next;
            });
            requestKey.current = crypto.randomUUID();
            setUnconfirmed(false);
            setRemovedFile(null);
          }}
        >
          Undo remove document
        </Button>
      )}
      <p role="status" aria-live="polite">
        {notice}
      </p>
      {unconfirmed && (
        <div className="upload-recovery-actions">
          <Button
            disabled={
              sending ||
              pending ||
              !files.length ||
              files.some((file) => Boolean(fileProblem(file)))
            }
            onClick={() => form.current?.requestSubmit()}
          >
            Retry upload
          </Button>
          <Button onClick={() => setJobsRefresh((value) => value + 1)}>
            Refresh upload status
          </Button>
        </div>
      )}
      {!pending &&
        jobs.some((job) => job.state === "succeeded") &&
        collection.active_snapshot && (
          <Notice
            action={<Button onClick={onSearch}>Search your papers</Button>}
          >
            Your papers are ready. Find a passage, explore a method, or follow a
            research question.
          </Notice>
        )}
      <Disclosure className="upload-help">
        <summary>Which PDFs work best?</summary>
        <p>
          Use unencrypted PDFs with selectable text. Scanned papers need OCR
          before uploading. Keep each PDF under 100 pages. Filenames become
          paper titles, so use a recognizable name.
        </p>
      </Disclosure>
      {jobs.length > 0 && (
        <Disclosure open>
          <summary>Processing activity</summary>
          <ul className="jobs">
            {jobs.map((job) => (
              <li key={job.job_id}>
                <StatusBadge
                  tone={
                    job.state === "failed"
                      ? "error"
                      : job.state === "succeeded"
                        ? "success"
                        : "info"
                  }
                >
                  {stateLabel(job.state)}
                </StatusBadge>
                <span>
                  {job.state === "succeeded"
                    ? "Snapshot activated. Ready to search."
                    : job.state === "failed"
                      ? (failures[job.error_code ?? ""] ??
                        "Processing failed. Check the worker and retry the upload.")
                      : job.state === "cancelled"
                        ? "Processing cancelled."
                        : (stages[job.stage] ?? "Processing source")}
                </span>
                {job.state === "retry_wait" && (
                  <small>Waiting before an automatic retry.</small>
                )}
                <small>
                  Job {job.job_id.slice(0, 8)}
                  {job.output_snapshot &&
                    ` · Snapshot ${job.output_snapshot.slice(0, 15)}…`}
                </small>
                <UploadProgress job={job} />
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </Surface>
  );
}
