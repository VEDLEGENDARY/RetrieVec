import { useEffect, useRef, useState } from "react";
import { api, type Collection, type Job, type Session } from "./api";

const stages: Record<string, string> = {
  queued: "Waiting for the worker", extract: "Extracting document text", chunk: "Preparing passages",
  embed: "Encoding passages", sparse_build: "Building the search index",
  validate: "Checking snapshot artifacts", activate: "Activating the searchable snapshot",
};
const failures: Record<string, string> = {
  invalid_input: "Could not extract usable text. Use unencrypted, text-based PDFs (100 pages maximum) or UTF-8 text.",
  unavailable: "A service is unavailable. Transient failures retry automatically.",
  stale_parent: "The collection changed during processing. Select the files and submit again.",
  attempts_exhausted: "Automatic retries were exhausted. Check the worker, then submit the files again.",
  extraction_timeout: "Text extraction exceeded its time limit. Try a smaller document.",
  encrypted_pdf: "This PDF is encrypted. Upload an unencrypted copy.",
  ocr_required: "No readable text was found. Scanned PDFs require OCR, which is not supported yet.",
};

export function Uploads({ collection, session, refresh, fail }: {
  collection: Collection; session: Session; refresh: () => Promise<void>; fail: (error: unknown) => void;
}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const observed = useRef(new Set<string>());
  useEffect(() => {
    if (!collection.can_manage) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const values = await api<Job[]>(`/api/v1/collections/${collection.collection_id}/jobs`, { signal: controller.signal });
        if (!live) return;
        setJobs(values);
        const completed = values.filter(job => job.state === "succeeded" && !observed.current.has(job.job_id));
        values.forEach(job => { if (job.state === "succeeded") observed.current.add(job.job_id); });
        if (completed.length) await refresh();
      } catch (error) { if (live) fail(error); }
      finally { if (live) timer = setTimeout(poll, 2500); }
    }
    void poll();
    return () => { live = false; controller.abort(); clearTimeout(timer); };
  }, [collection.collection_id, collection.can_manage, refresh, fail]);
  async function submit(event: React.SubmitEvent) {
    event.preventDefault();
    const files = Array.from(input.current?.files ?? []);
    if (!files.length) return;
    if (files.length > 10 || files.some(file => file.size > 25 * 1024 * 1024)) {
      setNotice("Choose up to 10 files, no larger than 25 MiB each."); return;
    }
    setSending(true); setNotice("Sending original files…");
    const body = new FormData(); files.forEach(file => body.append("files", file));
    try {
      const job = await api<Job>(`/api/v1/collections/${collection.collection_id}/uploads`, {
        method: "POST", body, headers: { "Idempotency-Key": crypto.randomUUID() },
      }, session.csrf_token);
      setJobs(current => [job, ...current.filter(item => item.job_id !== job.job_id)]);
      setNotice("Accepted for processing. Documents become searchable after snapshot activation.");
      if (input.current) input.current.value = "";
    } catch (error) { fail(error); setNotice("Upload was not confirmed. Refresh job status before resubmitting."); }
    finally { setSending(false); }
  }
  if (!collection.can_manage) return <p className="muted">This curated collection is managed by its owner.</p>;
  const pending = jobs.some(job => ["queued", "running", "retry_wait"].includes(job.state));
  return <section className="uploads" aria-labelledby="upload-heading">
    <div><h2 id="upload-heading">Add to your sources</h2><p>Text PDFs, plain text or Markdown. Up to 10 files · 25 MiB each · 100 PDF pages.</p></div>
    <form onSubmit={submit}><label htmlFor="documents">Choose documents</label><input id="documents" ref={input} type="file" accept=".pdf,.txt,.md" multiple required disabled={sending || pending} />
      <button className="primary" type="submit" disabled={sending || pending}>{sending ? "Sending…" : pending ? "Processing current upload…" : "Upload documents"}</button></form>
    <p role="status" aria-live="polite">{notice}</p>
    {jobs.length > 0 && <details open><summary>Processing activity</summary><ul className="jobs">{jobs.map(job => <li key={job.job_id}>
      <span className={`status ${job.state}`}>{job.state === "succeeded" ? "Searchable" : job.state.replaceAll("_", " ")}</span>
      <span>{job.state === "succeeded" ? "Snapshot activated. Ready to search." : job.state === "failed" ? failures[job.error_code ?? ""] ?? "Processing failed. Check the worker and retry the upload." : job.state === "cancelled" ? "Processing cancelled." : stages[job.stage] ?? job.stage}</span>
      {job.state === "retry_wait" && <small>Waiting before an automatic retry.</small>}
      <small>Job {job.job_id.slice(0, 8)}{job.output_snapshot && ` · Snapshot ${job.output_snapshot.slice(0, 15)}…`}</small>
    </li>)}</ul></details>}
  </section>;
}
