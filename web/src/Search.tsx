import { useEffect, useRef, useState } from "react";
import { AdvancedEvidence } from "./AdvancedEvidence";
import {
  BookmarkPlus,
  BookmarkCheck,
  SlidersHorizontal,
  History,
  Search as SearchIcon,
  X,
} from "lucide-react";
import { EvidenceTray, passageKey, type SavedPassage } from "./EvidenceTray";
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
  const [compact, setCompact] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [filter, setFilter] = useState("");
  const [method, setMethod] = useState("all");
  const [shortlist, setShortlist] = useState<SavedPassage[]>([]);
  const [notice, setNotice] = useState("");
  const [recent, setRecent] = useState<
    { query: string; mode: string; retrieval: string }[]
  >([]);
  const trigger = useRef<HTMLButtonElement | null>(null);
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
        setFilter("");
        setMethod("all");
        setRecent((current) =>
          [
            { query, mode, retrieval },
            ...current.filter(
              (item) =>
                item.query !== query ||
                item.mode !== mode ||
                item.retrieval !== retrieval,
            ),
          ].slice(0, 5),
        );
      }
    } catch (error) {
      if (!controller.signal.aborted) fail(error);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function inspect(hit: Hit, button: HTMLButtonElement) {
    trigger.current = button;
    setSelected(hit);
    setSourceError("");
    setTimeout(() => inspector.current?.focus(), 0);
  }
  function closeInspector() {
    setSelected(null);
    trigger.current?.focus();
  }
  function save(hit: Hit) {
    if (!result) return;
    const item = {
      hit,
      snapshot_id: result.snapshot_id,
      query: result.query,
      methods: Object.entries(result.results)
        .filter(([, value]) =>
          value.hits.some((candidate) => candidate.chunk_id === hit.chunk_id),
        )
        .map(([name]) => name),
    };
    if (shortlist.some((saved) => passageKey(saved) === passageKey(item))) {
      setShortlist((current) =>
        current.filter((saved) => passageKey(saved) !== passageKey(item)),
      );
      setNotice("Passage removed from the shortlist.");
    } else if (shortlist.length < 6) {
      setShortlist((current) => [...current, item]);
      setNotice("Passage added to the evidence shortlist.");
    } else
      setNotice(
        "Your shortlist has six passages. Remove one before adding another.",
      );
  }
  const sourceURL =
    selected?.source_id && result
      ? `/api/v1/sources/${selected.source_id}?snapshot_id=${encodeURIComponent(result.snapshot_id)}`
      : null;
  return (
    <section aria-labelledby="search-heading">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Evidence workbench</p>
          <h2 id="search-heading">Ask your sources</h2>
          <p>
            Follow an idea across your papers, then compare the passages that
            matter.
          </p>
        </div>
        <SearchIcon size={28} aria-hidden="true" />
      </div>
      <form className="search-form" onSubmit={submit}>
        <label htmlFor="question">Research question</label>
        <textarea
          id="question"
          rows={2}
          maxLength={4096}
          required
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (
              (event.ctrlKey || event.metaKey) &&
              event.key === "Enter" &&
              !busy &&
              collection.active_snapshot
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
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
          {busy && (
            <button
              type="button"
              onClick={() => {
                request.current?.abort();
                setBusy(false);
                setNotice(
                  "Search cancelled. Previous results are still available.",
                );
              }}
            >
              Cancel search
            </button>
          )}
        </div>
        {!collection.active_snapshot && (
          <p className="muted">
            Search unlocks after the first upload finishes processing.
          </p>
        )}
      </form>
      {recent.length > 0 && (
        <details className="recent-searches">
          <summary>
            <History size={16} aria-hidden="true" /> Recent searches in this
            collection
          </summary>
          <div>
            {recent.map((item, index) => (
              <button
                key={`${item.query}-${index}`}
                onClick={() => {
                  setQuery(item.query);
                  setMode(item.mode);
                  setRetrieval(item.retrieval);
                  document.getElementById("question")?.focus();
                }}
              >
                <span>{item.query}</span>
                <small>
                  {item.retrieval === "compare"
                    ? "Compare all methods"
                    : labels[item.retrieval]}
                </small>
              </button>
            ))}
          </div>
        </details>
      )}
      <EvidenceTray
        items={shortlist}
        collectionId={collection.collection_id}
        remove={(key) =>
          setShortlist((current) =>
            current.filter((item) => passageKey(item) !== key),
          )
        }
      />
      <p role="status" className="interaction-notice">
        {notice}
      </p>
      <p role="status" aria-live="polite">
        {busy
          ? "Searching one pinned snapshot…"
          : result
            ? `Results for “${result.query}”`
            : ""}
      </p>
      {result && (
        <>
          <div className="result-toolbar">
            <p>
              <strong>
                {
                  new Set(
                    Object.values(result.results).flatMap((value) =>
                      value.hits.map((hit) => hit.chunk_id),
                    ),
                  ).size
                }{" "}
                unique passages
              </strong>
              <br />
              Returned from one pinned snapshot.
            </p>
            <button
              type="button"
              aria-pressed={compact}
              onClick={() => setCompact((value) => !value)}
            >
              {compact ? "Show full excerpts" : "Compact results"}
            </button>
          </div>
          <div className="evidence-controls">
            <SlidersHorizontal size={18} aria-hidden="true" />
            <label>
              Filter returned passages
              <input
                type="search"
                value={filter}
                placeholder="Find a title or phrase…"
                onChange={(event) => setFilter(event.target.value)}
              />
            </label>
            <label>
              Show retrieval method
              <select
                value={method}
                onChange={(event) => setMethod(event.target.value)}
              >
                <option value="all">All returned methods</option>
                {Object.keys(result.results).map((name) => (
                  <option key={name} value={name}>
                    {labels[name] ?? name}
                  </option>
                ))}
              </select>
            </label>
            <small>
              Filters refine these results without running another search.
            </small>
          </div>
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
            <div className={compact ? "rankings compact" : "rankings"}>
              {Object.entries(result.results)
                .filter(([name]) => method === "all" || name === method)
                .map(([mode, value]) => (
                  <section
                    key={mode}
                    className="ranking"
                    aria-label={labels[mode]}
                  >
                    <h3>{labels[mode]}</h3>
                    <small>
                      {
                        value.hits.filter((hit) =>
                          `${hit.title} ${hit.text}`
                            .toLowerCase()
                            .includes(filter.toLowerCase()),
                        ).length
                      }{" "}
                      shown / {value.hits.length} returned ·{" "}
                      {value.total_matches} candidates
                    </small>
                    {!value.hits.some((hit) =>
                      `${hit.title} ${hit.text}`
                        .toLowerCase()
                        .includes(filter.toLowerCase()),
                    ) && (
                      <p className="no-results">
                        {filter
                          ? "No returned passages match this filter. Clear it or try another phrase."
                          : "No matching passages. Try a different question."}
                      </p>
                    )}
                    <ol>
                      {value.hits
                        .filter((hit) =>
                          `${hit.title} ${hit.text}`
                            .toLowerCase()
                            .includes(filter.toLowerCase()),
                        )
                        .map((hit) => (
                          <li key={hit.chunk_id} value={hit.rank}>
                            <button
                              className={
                                selected?.chunk_id === hit.chunk_id
                                  ? "hit active"
                                  : "hit"
                              }
                              onClick={(event) =>
                                inspect(hit, event.currentTarget)
                              }
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
                            <button
                              className="shortlist-action"
                              aria-pressed={shortlist.some(
                                (item) =>
                                  item.snapshot_id === result.snapshot_id &&
                                  item.hit.chunk_id === hit.chunk_id,
                              )}
                              onClick={() => save(hit)}
                            >
                              {shortlist.some(
                                (item) =>
                                  item.snapshot_id === result.snapshot_id &&
                                  item.hit.chunk_id === hit.chunk_id,
                              ) ? (
                                <BookmarkCheck size={15} aria-hidden="true" />
                              ) : (
                                <BookmarkPlus size={15} aria-hidden="true" />
                              )}{" "}
                              Shortlist passage
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
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    event.stopPropagation();
                    closeInspector();
                  }
                }}
              >
                <div className="inspector-heading">
                  <h3>Evidence inspector</h3>
                  <button
                    aria-label="Close evidence inspector"
                    onClick={closeInspector}
                  >
                    <X size={18} />
                  </button>
                </div>
                <h2>{selected.title}</h2>
                <p className="eyebrow">
                  PAPER EVIDENCE
                  {selected.page_range && ` · PAGE ${selected.page_range[0]}`}
                </p>
                <blockquote>{selected.text}</blockquote>
                <small>Chunk {selected.chunk_id}</small>
                {selected.evidence_object_id ? (
                  <AdvancedEvidence
                    key={selected.chunk_id}
                    collectionId={collection.collection_id}
                    snapshotId={result.snapshot_id}
                    chunkId={selected.chunk_id}
                  />
                ) : sourceURL ? (
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
