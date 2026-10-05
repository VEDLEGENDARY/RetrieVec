import { BasedOn } from "./BasedOn";
import { SectionField } from "./SectionField";
import {
  Button,
  ActionLink,
  Field,
  Input,
  Select,
  Textarea,
  LoadingState,
  Disclosure,
  More,
} from "./ui";
import { SearchRankings, labels } from "./SearchRankings";
import { EvidencePanel } from "./EvidencePanel";
import { useDraft } from "./drafts";
import { useEffect, useRef, useState } from "react";
import { AdvancedEvidence } from "./AdvancedEvidence";
import { SlidersHorizontal, History, Search as SearchIcon } from "lucide-react";
import { EvidenceTray, passageKey, type SavedPassage } from "./EvidenceTray";
import {
  api,
  type Collection,
  type Hit,
  type SearchResult,
  type Session,
} from "./api";

export function Search({
  collection,
  session,
  fail,
}: {
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  const [query, setQuery, draftSaved] = useDraft(
    session.principal_id,
    collection.collection_id,
    "question",
  );
  const [mode, setMode] = useState("free_text");
  const [section, setSection] = useState("");
  const [retrieval, setRetrieval] = useState("hybrid");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [selected, setSelected] = useState<Hit | null>(null);
  const [busy, setBusy] = useState(false);
  const [compact, setCompact] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [filter, setFilter] = useState("");
  const [method, setMethod] = useState("all");
  const [shortlist, setShortlist] = useState<SavedPassage[]>([]);
  const [removed, setRemoved] = useState<{
    item: SavedPassage;
    index: number;
  } | null>(null);
  function removePassage(key: string) {
    const index = shortlist.findIndex((item) => passageKey(item) === key);
    if (index < 0) return;
    setRemoved({ item: shortlist[index], index });
    setShortlist((current) =>
      current.filter((item) => passageKey(item) !== key),
    );
    setNotice("Passage removed from the shortlist.");
  }
  const [notice, setNotice] = useState("");
  const [recent, setRecent] = useState<
    { query: string; mode: string; retrieval: string }[]
  >([]);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const request = useRef<AbortController | null>(null);
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
            ...(section ? { section } : {}),
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
      removePassage(passageKey(item));
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
        <Field label="Research question">
          <Textarea
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
                !event.nativeEvent.isComposing &&
                !busy &&
                collection.active_snapshot
              ) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="How does dense retrieval compare with lexical matching?"
          />
        </Field>
        <p className="muted">
          {draftSaved
            ? "Draft saved on this device for 7 days. Cleared on sign out."
            : "Device storage is unavailable. Keep this tab open to retain your draft."}
        </p>
        <div className="search-controls">
          <More label="More search options">
            <Button
              id="compare-methods"
              type="button"
              onClick={() => {
                setMode("free_text");
                setRetrieval("compare");
              }}
            >
              Compare methods
            </Button>
            <Field label="Query syntax">
              <Select
                id="parser"
                value={mode}
                onChange={(event) => {
                  setMode(event.target.value);
                  if (event.target.value === "structured")
                    setRetrieval("sparse");
                }}
              >
                <option value="free_text">Natural language</option>
                <option value="structured">Boolean / phrase</option>
              </Select>
            </Field>
            <Field label="Retrieval method">
              <Select
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
              </Select>
            </Field>
          </More>
          <More label="More section filters">
            <SectionField
              value={section}
              onChange={setSection}
              disabled={busy}
            />
          </More>
          <Button
            type="submit"
            loading={busy}
            title="Search evidence (Ctrl or Command + Enter)"
            aria-keyshortcuts="Control+Enter Meta+Enter"
            className="primary"
            disabled={busy || !collection.active_snapshot}
          >
            {busy ? "Searching…" : "Search evidence"}
          </Button>
          {busy && (
            <Button
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
            </Button>
          )}
        </div>
        {!collection.active_snapshot && (
          <p className="muted">
            Search unlocks after the first upload finishes processing.
          </p>
        )}
      </form>
      <More label="More evidence options">
        {recent.length > 0 && (
          <Disclosure id="recent-searches" className="recent-searches">
            <summary>
              <History size={16} aria-hidden="true" /> Recent searches in this
              collection
            </summary>
            <div>
              {recent.map((item, index) => (
                <Button
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
                </Button>
              ))}
            </div>
          </Disclosure>
        )}
        <EvidenceTray
          items={shortlist}
          collectionId={collection.collection_id}
          remove={removePassage}
        />
      </More>
      <p role="status" className="interaction-notice">
        {notice}
        {removed && (
          <Button
            type="button"
            disabled={
              shortlist.length >= 6 ||
              shortlist.some(
                (item) => passageKey(item) === passageKey(removed.item),
              )
            }
            onClick={() => {
              setShortlist((current) => {
                const next = [...current];
                next.splice(
                  Math.min(removed.index, next.length),
                  0,
                  removed.item,
                );
                return next;
              });
              setRemoved(null);
              setNotice("Passage restored to the shortlist.");
            }}
          >
            Undo remove passage
          </Button>
        )}
      </p>
      {busy && <LoadingState label="Finding evidence in your collection…" />}
      <p role="status" aria-live="polite">
        {busy
          ? "Searching one pinned snapshot…"
          : result
            ? `Results for “${result.query}”`
            : ""}
      </p>
      {result && (
        <>
          <BasedOn
            kind="search"
            snapshot={result.snapshot_id}
            candidates={Object.values(result.results)
              .flatMap((value) => value.hits)
              .map((hit) => ({
                id: hit.chunk_id,
                content: (
                  <Button
                    onClick={(event) => inspect(hit, event.currentTarget)}
                  >
                    {hit.title}
                  </Button>
                ),
              }))}
          />
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
            <Button
              id="excerpt-display"
              type="button"
              aria-pressed={compact}
              onClick={() => setCompact((value) => !value)}
            >
              {compact ? "Show full excerpts" : "Compact results"}
            </Button>
          </div>
          <More label="More result options">
            <div className="evidence-controls">
              <SlidersHorizontal size={18} aria-hidden="true" />
              <Field label="Filter returned passages">
                <Input
                  type="search"
                  value={filter}
                  id="passage-filter"
                  placeholder="Find a title or phrase…"
                  onChange={(event) => setFilter(event.target.value)}
                />
              </Field>
              <Field label="Show retrieval method">
                <Select
                  value={method}
                  onChange={(event) => setMethod(event.target.value)}
                >
                  <option value="all">All returned methods</option>
                  {Object.keys(result.results).map((name) => (
                    <option key={name} value={name}>
                      {labels[name] ?? name}
                    </option>
                  ))}
                </Select>
              </Field>
              <small>
                Filters refine these results without running another search.
              </small>
            </div>
            <Disclosure id="search-diagnostics" className="diagnostics">
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
            </Disclosure>
          </More>
          <div
            className={
              selected ? "evidence-layout inspecting" : "evidence-layout"
            }
          >
            <SearchRankings
              result={result}
              compact={compact}
              method={method}
              filter={filter}
              selected={selected}
              shortlist={shortlist}
              inspect={inspect}
              save={save}
            />
            {selected && (
              <EvidencePanel
                title={selected.title}
                text={selected.text}
                pages={selected.page_range}
                snapshot={result.snapshot_id}
                onClose={closeInspector}
              >
                {selected.evidence_object_id ? (
                  <AdvancedEvidence
                    key={selected.chunk_id}
                    collectionId={collection.collection_id}
                    snapshotId={result.snapshot_id}
                    chunkId={selected.chunk_id}
                  />
                ) : sourceURL ? (
                  <>
                    <ActionLink
                      className="source-link"
                      target="_blank"
                      rel="noreferrer"
                      href={`${sourceURL}#page=${selected.page_range?.[0] ?? 1}`}
                    >
                      Open original source
                    </ActionLink>
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
              </EvidencePanel>
            )}
          </div>
        </>
      )}
    </section>
  );
}
