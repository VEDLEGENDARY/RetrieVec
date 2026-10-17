import type { Job } from "../../api";
import { Disclosure } from "../../ui";
export type FileProgress = {
  source_id: string;
  name: string;
  size_bytes: number;
  media_type: string;
  state: string;
  stage: string;
  stage_scope: "batch";
  provenance: null | {
    source_sha256: string;
    extraction_version: string;
    extractors: { name: string; revision: string }[];
    ocr_used: boolean | null;
    derivations: string[];
  };
};
const steps: Record<string, string> = {
  queued: "Waiting for the worker",
  extract: "Extracting text",
  chunk: "Preparing passages",
  embed: "Encoding passages",
  sparse_build: "Building the search index",
  validate: "Validating the snapshot",
  activate: "Activating the snapshot",
};
function isFileProgress(value: unknown): value is FileProgress {
  if (!value || typeof value !== "object") return false;
  const file = value as FileProgress;
  return (
    typeof file.source_id === "string" &&
    typeof file.name === "string" &&
    Number.isFinite(file.size_bytes) &&
    typeof file.media_type === "string" &&
    typeof file.stage === "string" &&
    (file.provenance === null ||
      (typeof file.provenance === "object" &&
        typeof file.provenance.source_sha256 === "string" &&
        typeof file.provenance.extraction_version === "string" &&
        Array.isArray(file.provenance.extractors) &&
        file.provenance.extractors.every(
          (item) =>
            item &&
            typeof item.name === "string" &&
            typeof item.revision === "string",
        )))
  );
}
export function UploadProgress({ job }: { job: Job }) {
  const files = Array.isArray(job.progress?.files)
    ? job.progress.files.filter(isFileProgress)
    : [];
  if (!files.length)
    return <p className="muted">This job has no retained file details.</p>;
  return (
    <ul className="ingestion-files">
      {files.map((file) => (
        <li key={file.source_id} className="ingestion-file">
          <div>
            <strong>{file.name}</strong>
            <small>
              <span className="metric">
                {file.size_bytes.toLocaleString()} bytes
              </span>{" "}
              · {file.media_type}
            </small>
          </div>
          <p>
            {job.state === "succeeded"
              ? "Ready to search"
              : job.state === "failed"
                ? "Batch failed. See the processing message above."
                : job.state === "cancelled"
                  ? "Batch cancelled"
                  : `Batch stage: ${steps[file.stage] ?? file.stage}`}
          </p>
          {["running", "queued", "retry_wait"].includes(job.state) && (
            <progress aria-label={`Ingestion for ${file.name}`} />
          )}
          {job.state === "succeeded" && (
            <Disclosure open>
              <summary>Extraction provenance for {file.name}</summary>
              {file.provenance ? (
                <dl>
                  <dt>Extractor</dt>
                  <dd>
                    {file.provenance.extractors.length
                      ? file.provenance.extractors
                          .map(
                            (extractor) =>
                              `${extractor.name} (${extractor.revision})`,
                          )
                          .join(", ")
                      : "Extractor not reported"}
                  </dd>
                  <dt>OCR</dt>
                  <dd>
                    {file.provenance.ocr_used === true
                      ? "Used"
                      : file.provenance.ocr_used === false
                        ? "Not used"
                        : "Not reported"}
                  </dd>
                  <dt>Extraction version</dt>
                  <dd>
                    <code>{file.provenance.extraction_version}</code>
                  </dd>
                  <dt>Source SHA-256</dt>
                  <dd>
                    <code>{file.provenance.source_sha256}</code>
                  </dd>
                </dl>
              ) : (
                <p>
                  Extraction provenance was not retained for this older job.
                </p>
              )}
            </Disclosure>
          )}
        </li>
      ))}
    </ul>
  );
}
