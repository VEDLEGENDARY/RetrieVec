import { useEffect, useState } from "react";
import { BookOpenText, FileText, RefreshCw } from "lucide-react";
import { api, APIError, type Collection } from "./api";
import {
  ActionLink,
  Button,
  Field,
  Input,
  LoadingState,
  Notice,
  StatusBadge,
  Surface,
} from "./ui";
import { errorMessage, stateLabel } from "./presentation";

type Paper = {
  source_id: string;
  display_name: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
  state: string;
};
type PaperPage = {
  items: Paper[];
  next_cursor: string | null;
};

export function PaperLibrary({
  collection,
  fail,
}: {
  collection: Collection;
  fail: (error: unknown) => void;
}) {
  const [query, setQuery] = useState("");
  const [cursors, setCursors] = useState([""]);
  const [pageIndex, setPageIndex] = useState(0);
  const cursor = cursors[pageIndex];
  function restartPages() {
    setCursors([""]);
    setPageIndex(0);
  }
  const [page, setPage] = useState<PaperPage | null>(null);
  const [failed, setFailed] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setPage(null);
    setFailed("");
    async function load() {
      try {
        const params = new URLSearchParams({
          q: query,
          limit: "25",
        });
        if (cursor) params.set("after", cursor);
        const value = await api<PaperPage>(
          `/api/v1/collections/${collection.collection_id}/papers?${params}`,
          { signal: controller.signal },
        );
        if (
          !value ||
          !Array.isArray(value.items) ||
          value.items.some(
            (paper) =>
              !paper ||
              typeof paper.source_id !== "string" ||
              typeof paper.display_name !== "string" ||
              typeof paper.media_type !== "string" ||
              typeof paper.state !== "string" ||
              !Number.isSafeInteger(paper.size_bytes) ||
              paper.size_bytes < 0 ||
              typeof paper.created_at !== "string" ||
              !Number.isFinite(Date.parse(paper.created_at)),
          ) ||
          !(value.next_cursor === null || typeof value.next_cursor === "string")
        )
          throw new Error(
            "The server returned an incomplete paper library. Refresh to try again.",
          );
        if (!controller.signal.aborted) {
          setPage(value);
          setFailed("");
          timer = setTimeout(load, 5000);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setFailed(errorMessage(error));
          if (error instanceof APIError && [401, 404].includes(error.status))
            fail(error);
        }
      }
    }
    timer = setTimeout(load, query ? 250 : 0);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [
    collection.collection_id,
    collection.active_snapshot,
    query,
    cursor,
    revision,
    fail,
  ]);

  return (
    <Surface className="paper-library" aria-labelledby="library-heading">
      <div className="library-heading">
        <div>
          <h2 id="library-heading">Your paper library</h2>
          <p>Original uploads, kept together with their processing status.</p>
        </div>
        <BookOpenText size={24} aria-hidden="true" />
      </div>
      <div className="library-tools">
        <Field label="Find an uploaded paper">
          <Input
            type="search"
            maxLength={120}
            value={query}
            placeholder="Search paper filenames…"
            onChange={(event) => {
              setQuery(event.target.value);
              restartPages();
            }}
          />
        </Field>
        <Button
          aria-label="Refresh paper library"
          onClick={() => setRevision((value) => value + 1)}
        >
          <RefreshCw size={16} aria-hidden="true" /> Refresh
        </Button>
      </div>
      {failed ? (
        <Notice
          error
          action={
            <Button onClick={() => setRevision((value) => value + 1)}>
              Retry loading papers
            </Button>
          }
        >
          {failed}
        </Notice>
      ) : !page ? (
        <LoadingState label="Loading your papers…" />
      ) : page.items.length ? (
        <>
          <p className="muted" role="status">
            {page.items.length} uploaded{" "}
            {page.items.length === 1 ? "file" : "files"} on this page
            {query ? ` matching “${query}”` : ""}
          </p>
          <ul className="paper-list">
            {page.items.map((paper) => (
              <li key={paper.source_id}>
                <span className="paper-file-icon">
                  <FileText size={22} aria-hidden="true" />
                </span>
                <div className="paper-file-details">
                  <h3>{paper.display_name}</h3>
                  <p>
                    {paper.media_type === "application/pdf"
                      ? "PDF paper"
                      : "Text or notes"}{" "}
                    · {Math.max(1, Math.round(paper.size_bytes / 1024))} KiB ·
                    Added{" "}
                    {new Intl.DateTimeFormat(undefined, {
                      dateStyle: "medium",
                    }).format(new Date(paper.created_at))}
                  </p>
                </div>
                <StatusBadge
                  tone={
                    paper.state === "succeeded"
                      ? "success"
                      : paper.state === "failed"
                        ? "error"
                        : "info"
                  }
                >
                  {paper.state === "succeeded"
                    ? "Ready"
                    : stateLabel(paper.state)}
                </StatusBadge>
                {paper.state === "succeeded" && collection.active_snapshot && (
                  <ActionLink
                    className="paper-original"
                    href={`/api/v1/sources/${encodeURIComponent(paper.source_id)}?snapshot_id=${encodeURIComponent(collection.active_snapshot)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open original ${paper.display_name} in a new tab`}
                  >
                    Open original
                  </ActionLink>
                )}
              </li>
            ))}
          </ul>
          {(pageIndex > 0 || page.next_cursor) && (
            <nav
              className="library-pagination"
              aria-label="Paper library pages"
            >
              <Button
                disabled={pageIndex === 0}
                onClick={() => setPageIndex((value) => value - 1)}
              >
                Previous papers
              </Button>
              <span className="muted">Page {pageIndex + 1}</span>
              <Button
                disabled={!page.next_cursor}
                onClick={() => {
                  if (!page.next_cursor) return;
                  setCursors((values) => [
                    ...values.slice(0, pageIndex + 1),
                    page.next_cursor!,
                  ]);
                  setPageIndex((value) => value + 1);
                }}
              >
                Next papers
              </Button>
            </nav>
          )}
        </>
      ) : (
        <div className="library-empty">
          <FileText size={24} aria-hidden="true" />
          <h3>
            {query ? "No matching papers" : "Your uploads will appear here"}
          </h3>
          <p>
            {query
              ? "Try a different filename or clear the search."
              : collection.visibility === "curated"
                ? "This starter collection contains imported research records. Create a private collection to add your own PDFs and notes."
                : "Add papers above to build a searchable library for your research."}
          </p>
          {query && (
            <Button
              onClick={() => {
                setQuery("");
                restartPages();
              }}
            >
              Clear paper search
            </Button>
          )}
        </div>
      )}
    </Surface>
  );
}
