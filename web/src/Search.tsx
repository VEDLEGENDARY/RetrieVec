import { useEffect, useRef, useState } from "react";
import {
  api,
  type Collection,
  type Hit,
  type SearchResult,
  type Session,
} from "./api";

const labels: Record<string, string> = {
  sparse: "Sparse · BM25",
  dense: "Dense · Cosine",
  hybrid: "Hybrid · RRF",
};
export function Search({
  collection,
  session,
  fail,
}: {
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("free_text");
  const [retrieval, setRetrieval] = useState("compare");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [selected, setSelected] = useState<Hit | null>(null);
  const [busy, setBusy] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const request = useRef<AbortController | null>(null);
  const inspector = useRef<HTMLElement>(null);
  useEffect(
    () => () => {
      request.current?.abort();
    },
    [],
  );
  async function submit(event: React.SubmitEvent) {
    event.preventDefault();
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const value = await api<SearchResult>(
        "/api/v1/search",
        {
          method: "POST",
          signal: controller.signal,
          body: JSON.stringify({
            collection_id: collection.collection_id,
            query,
            mode,
            retrieval,
          }),
        },
        session.csrf_token,
      );
      if (!controller.signal.aborted) {
        setResult(value);
        setSelected(null);
        setSourceError("");
      }
    } catch (error) {
      if (!controller.signal.aborted) fail(error);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function inspect(hit: Hit) {
    setSelected(hit);
    setSourceError("");
    setTimeout(() => inspector.current?.focus(), 0);
  }
  const sourceURL =
    selected?.source_id && result
      ? `/api/v1/sources/${selected.source_id}?snapshot_id=${encodeURIComponent(result.snapshot_id)}`
      : null;
  return (
    <section aria-labelledby="search-heading">
      <h2 id="search-heading">Ask your sources</h2>
      <form className="search-form" onSubmit={submit}>
        <label htmlFor="question">Research question</label>
        <textarea
          id="question"
          rows={2}
          maxLength={4096}
          required
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="How does dense retrieval compare with lexical matching?"
        />
        <div className="search-controls">
          <label htmlFor="parser">Query syntax</label>
          <select
            id="parser"
            value={mode}
            onChange={(event) => {
              setMode(event.target.value);
              if (event.target.value === "structured") setRetrieval("sparse");
            }}
          >
            <option value="free_text">Natural language</option>
            <option value="structured">Boolean / phrase</option>
          </select>
          <label htmlFor="retrieval">Retrieval method</label>
          <select
            id="retrieval"
            value={retrieval}
            onChange={(event) => setRetrieval(event.target.value)}
          >
            <option value="compare" disabled={mode === "structured"}>
              Compare all three
            </option>
            <option value="sparse">Sparse</option>
            <option value="dense" disabled={mode === "structured"}>
              Dense
            </option>
            <option value="hybrid" disabled={mode === "structured"}>
              Hybrid
            </option>
          </select>
          <button
            type="submit"
            className="primary"
            disabled={busy || !collection.active_snapshot}
          >
            {busy ? "Searching…" : "Search evidence →"}
          </button>
        </div>
        {!collection.active_snapshot && (
          <p className="muted">
            Search unlocks after the first upload finishes processing.
          </p>
        )}
      </form>
      <p role="status" aria-live="polite">
        {busy
          ? "Searching one pinned snapshot…"
          : result
            ? `Results for “${result.query}”`
            : ""}
      </p>
      {result && (
        <>
          <details className="diagnostics">
            <summary>Snapshot and search diagnostics</summary>
            <p>
              Snapshot <code>{result.snapshot_id}</code>
            </p>
            <p>
              All methods below use this same snapshot. Scores have different
              meanings and are not a shared scale.
            </p>
            <pre>
              {JSON.stringify(
                Object.fromEntries(
                  Object.entries(result.results).map(([mode, value]) => [
                    mode,
                    value.configuration,
                  ]),
                ),
                null,
                2,
              )}
            </pre>
          </details>
          <div
            className={
              selected ? "evidence-layout inspecting" : "evidence-layout"
            }
          >
            <div className="rankings">
              {Object.entries(result.results).map(([mode, value]) => (
                <section
                  key={mode}
                  className="ranking"
                  aria-label={labels[mode]}
                >
                  <h3>{labels[mode]}</h3>
                  <small>{value.total_matches} candidates / matches</small>
                  {!value.hits.length && (
                    <p className="no-results">
                      No matching passages. Try a different question.
                    </p>
                  )}
                  <ol>
                    {value.hits.map((hit) => (
                      <li key={hit.chunk_id}>
                        <button
                          className={
                            selected?.chunk_id === hit.chunk_id
                              ? "hit active"
                              : "hit"
                          }
                          onClick={() => inspect(hit)}
                        >
                          <span className="hit-title">{hit.title}</span>
                          <span className="excerpt">{hit.text}</span>
                          <small>
                            {hit.page_range
                              ? `Page ${hit.page_range[0]}`
                              : "Page unavailable"}{" "}
                            ·{" "}
                            {mode === "sparse"
                              ? `BM25 ${hit.bm25_score?.toFixed(3)}`
                              : mode === "dense"
                                ? `Cosine ${hit.cosine_score?.toFixed(3)}`
                                : `RRF ${hit.rrf_score?.toFixed(5)}`}
                          </small>
                        </button>
                      </li>
                    ))}
                  </ol>
                </section>
              ))}
            </div>
            {selected && (
              <aside
                ref={inspector}
                tabIndex={-1}
                className="inspector"
                aria-label="Evidence inspector"
              >
                <div className="inspector-heading">
                  <h3>Evidence inspector</h3>
                  <button
                    aria-label="Close evidence inspector"
                    onClick={() => setSelected(null)}
                  >
                    ×
                  </button>
                </div>
                <h2>{selected.title}</h2>
                <p className="eyebrow">
                  PAPER EVIDENCE
                  {selected.page_range && ` · PAGE ${selected.page_range[0]}`}
                </p>
                <blockquote>{selected.text}</blockquote>
                <small>Chunk {selected.chunk_id}</small>
                {sourceURL ? (
                  <>
                    <a
                      className="button source-link"
                      target="_blank"
                      rel="noreferrer"
                      href={`${sourceURL}#page=${selected.page_range?.[0] ?? 1}`}
                    >
                      Open original source ↗
                    </a>
                    <iframe
                      title="Original source preview"
                      src={`${sourceURL}#page=${selected.page_range?.[0] ?? 1}`}
                      onError={() =>
                        setSourceError(
                          "Preview unavailable. Open the original source in a new tab.",
                        )
                      }
                    />
                    {sourceError && <p role="status">{sourceError}</p>}
                    <p className="muted">
                      The passage is shown separately; exact PDF highlights are
                      unavailable.
                    </p>
                  </>
                ) : (
                  <p>
                    Original file unavailable for this imported source. The
                    pinned extracted passage is shown above.
                  </p>
                )}
              </aside>
            )}
          </div>
        </>
      )}
    </section>
  );
}
