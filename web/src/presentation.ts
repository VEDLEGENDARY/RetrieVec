import { APIError } from "./api";

/** Presentation only. API enum values, state transitions, and error codes stay intact. */
const states: Record<string, string> = {
  queued: "Queued",
  running: "Processing",
  retry_wait: "Waiting to retry",
  succeeded: "Searchable",
  failed: "Failed",
  cancelled: "Cancelled",
  retrieving: "Finding passages",
  generating: "Generating cited answer",
  validating: "Checking citations",
  completed: "Completed",
};
export function stateLabel(state: string) {
  return states[state] ?? "Status unavailable";
}
export const exportLabels: Record<string, string> = {
  markdown: "Markdown",
  bibtex: "BibTeX",
  json: "JSON",
  csv: "CSV",
};

export function errorMessage(cause: unknown): string {
  if (!(cause instanceof APIError))
    return "The request could not be completed. Check your connection, then try again.";
  // Preserve server guidance, including uncertain upload completion and access distinctions.
  if (
    /try|retry|sign in|check|contact|choose|select|use |wait|reopen|remove|upload/i.test(
      cause.message,
    )
  )
    return cause.message;
  const action =
    cause.status === 403 || cause.status === 404
      ? "Choose an available collection or contact its owner."
      : cause.status === 400 || cause.status === 422
        ? "Review your input and try again."
        : "Try again shortly. If this continues, contact the workspace operator.";
  return `${cause.message.replace(/[.\s]+$/, "")}. ${action}`;
}
