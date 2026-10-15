import { useRef, useState } from "react";
import {
  BookmarkCheck,
  Download,
  Map,
  Search as SearchIcon,
} from "lucide-react";
import type { Collection, Hit, Session } from "../../api";
import { BasedOn } from "../../BasedOn";
import {
  Button,
  Disclosure,
  EmptyState,
  Field,
  Input,
  IconButton,
  More,
  Notice,
  Select,
} from "../../ui";
import { SectionField } from "../../SectionField";
import { MethodSwitch } from "./MethodSwitch";
import { CompareDrawer } from "./CompareDrawer";
import { RecentSearches } from "./RecentSearches";
import { PassageCard, PassageSkeleton } from "./PassageCard";
import { SearchInspector } from "./SearchInspector";
import { AtlasPanel } from "./AtlasPanel";
import { useEvidenceWorkbench } from "./useEvidenceWorkbench";
import { useCardReorder } from "./useCardReorder";
import { passageIdentity, queryKey } from "./lib/evidence";
import { methods, methodDetails, methodNames } from "./types";
import "./search.css";

export function SearchPage({
  collection,
  session,
  fail,
}: {
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  const w = useEvidenceWorkbench(collection, session, fail);
  const [comparisonOpen, setComparisonOpen] = useState(false),
    [compact, setCompact] = useState(false);
  const cards = useRef<HTMLOListElement>(null),
    inspectorTrigger = useRef<HTMLButtonElement | null>(null);
  const unique = new Set(
    Object.values(w.active?.result.results ?? {}).flatMap((ranking) =>
      ranking.hits.map((hit) => hit.chunk_id),
    ),
  ).size;
  const available = methods.filter(
    (method) => w.active?.result.results[method],
  );
  const missing = w.error && !!w.active;
  useCardReorder(
    cards,
    w.active ? queryKey(w.active.spec) : "",
    w.displayMethod,
    w.visible.map((passage) => passage.hit.chunk_id).join("\0"),
  );
  function inspect(hit: Hit, trigger: HTMLButtonElement) {
    inspectorTrigger.current = trigger;
    w.setSelected(hit);
  }
  const highlights = methods.flatMap((method) =>
    (w.active?.result.results[method]?.hits ?? []).map((hit) => ({
      passageId: hit.chunk_id,
      method,
      rank: hit.rank,
    })),
  );
  return (
    <section className="search-workbench" aria-labelledby="search-heading">
      <div className="workbench-heading">
        <div>
          <h2 id="search-heading">Ask your sources</h2>
          <p>
            Find a passage, compare its ranking, and follow it to the source.
          </p>
        </div>
        <RecentSearches
          items={w.recent}
          onSelect={(item) => {
            w.restore(item);
            requestAnimationFrame(() =>
              document.getElementById("question")?.focus(),
            );
          }}
        />
      </div>
      <form
        className="workbench-query"
        onSubmit={(event) => {
          event.preventDefault();
          w.submit();
        }}
      >
        <Field label="Research question">
          <Input
            id="question"
            type="search"
            value={w.query}
            onChange={(event) => w.setQuery(event.target.value)}
            maxLength={4096}
            required
            placeholder="Search for a finding, method, or limitation…"
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              if (event.nativeEvent.isComposing) {
                event.preventDefault();
                return;
              }
              if (
                (event.ctrlKey || event.metaKey) &&
                !w.busy &&
                collection.active_snapshot
              ) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
        </Field>
        <div className="query-actions">
          <MethodSwitch
            value={w.method}
            onChange={w.selectMethod}
            structured={w.mode === "structured"}
          />
          <Button
            type="submit"
            variant="primary"
            loading={w.busy}
            disabled={!w.query.trim() || !collection.active_snapshot}
            aria-keyshortcuts="Control+Enter Meta+Enter"
          >
            <SearchIcon aria-hidden="true" />
            Search collection
          </Button>
        </div>
        <p className="draft-note">
          {w.draftSaved
            ? "Draft saved on this device for 7 days. Cleared on sign out."
            : "Device storage is unavailable. Keep this tab open to retain your draft."}
        </p>
        <div className="workbench-options">
          {collection.active_snapshot && (
            <More label="Question suggestions">
              <div
                className="question-starters"
                role="group"
                aria-label="Question suggestions"
              >
                <span>Start with a question</span>
                {[
                  "What methods do these papers use?",
                  "What are the main findings?",
                  "What limitations do the authors report?",
                ].map((question) => (
                  <Button
                    key={question}
                    type="button"
                    disabled={w.busy}
                    onClick={() => {
                      w.setQuery(question);
                      document.getElementById("question")?.focus();
                    }}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            </More>
          )}
          <More label="More search options">
            <Button
              id="compare-methods"
              type="button"
              onClick={w.compareMethods}
            >
              Compare methods
            </Button>
            {w.compare && <p>All three methods will run on the next search.</p>}
            <Field label="Query syntax">
              <Select
                id="parser"
                value={w.mode}
                onChange={(event) => w.setMode(event.target.value)}
              >
                <option value="free_text">Natural language</option>
                <option value="structured">Boolean / phrase</option>
              </Select>
            </Field>
            <Field
              label="Experimental reranking"
              description="Optional second-pass hybrid ranking. Adds latency and may not improve results. Requires a locally cached model."
            >
              <Input
                id="experimental-rerank"
                type="checkbox"
                checked={w.rerank}
                disabled={
                  w.mode !== "free_text" || w.method !== "hybrid" || w.compare
                }
                onChange={(event) => w.setRerank(event.target.checked)}
              />
            </Field>
          </More>
          <More label="More section filters">
            <SectionField
              value={w.section}
              onChange={w.setSection}
              disabled={w.busy}
            />
          </More>
        </div>
      </form>
      <div className="workbench-tools">
        <div className="workbench-filter">
          <Field label="Filter returned passages">
            <Input
              id="passage-filter"
              type="search"
              value={w.filter}
              onChange={(event) => w.setFilter(event.target.value)}
              placeholder="Filter by a title or phrase…"
              disabled={!w.active}
            />
          </Field>
          <Field label="Show retrieval method">
            <Select
              value={w.methodFilter}
              onChange={(event) => w.setMethodFilter(event.target.value)}
              disabled={!w.active}
            >
              <option value="active">Current method</option>
              <option value="all">All returned methods</option>
              {available.map((method) => (
                <option key={method} value={method}>
                  {methodNames[method]} · {methodDetails[method]}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="shortlist-actions">
          <Button
            id="passage-shortlist"
            className="shortlist-chip"
            onClick={() => setComparisonOpen(true)}
            aria-haspopup="dialog"
          >
            <BookmarkCheck aria-hidden="true" />
            Shortlist <span className="count-pill">{w.shortlist.length}/6</span>
          </Button>
          <IconButton
            id="export-shortlist"
            aria-label="Export shortlist JSON"
            title="Export shortlist JSON"
            disabled={!w.shortlist.length}
            onClick={w.exportShortlist}
          >
            <Download aria-hidden="true" />
          </IconButton>
        </div>
      </div>
      <div className="workbench-feedback">
        <p role="status" aria-live="polite">
          <span>
            {w.busy
              ? "Searching one pinned snapshot…"
              : w.active
                ? `Results for “${w.active.spec.query}” · ${methodNames[w.displayMethod]}`
                : "Search your collection to find retained passages."}
          </span>
          {w.busy && <Button onClick={w.cancel}>Cancel search</Button>}
        </p>
        {w.notice && (
          <p role="status">
            {w.notice}
            {w.removed && (
              <Button onClick={w.undo} disabled={w.shortlist.length >= 6}>
                Undo remove passage
              </Button>
            )}
          </p>
        )}
        {w.error && (
          <Notice error>
            <span>
              {missing
                ? `${methodNames[w.method]} search is incomplete. Available ${methodNames[w.displayMethod]} results remain below. `
                : "Search failed. "}
              {w.error}
            </span>
            <Button onClick={w.retry}>Retry search</Button>
          </Notice>
        )}
        {w.active?.result.results.hybrid?.reranker?.status === "fallback" && (
          <Notice>
            Experimental reranking was unavailable. These results use the
            original hybrid order.
          </Notice>
        )}
        {w.active?.result.results.hybrid?.reranker?.status === "applied" && (
          <Notice>
            Experimental reranking applied. Ranking scores are not a measure of
            factual support.
          </Notice>
        )}
      </div>
      <div className="workbench-layout">
        <div className="workbench-reading">
          <div className="workbench-result-tools">
            {w.active && (
              <>
                <div className="result-toolbar">
                  <p>
                    <strong>{unique} unique passages</strong>
                    <br />
                    One pinned snapshot. Scores use different scales.
                  </p>
                  <Button
                    id="excerpt-display"
                    aria-pressed={compact}
                    onClick={() => setCompact((value) => !value)}
                  >
                    {compact ? "Show full excerpts" : "Compact results"}
                  </Button>
                </div>
                <BasedOn
                  kind="search"
                  snapshot={w.active.result.snapshot_id}
                  candidates={Object.values(w.active.result.results)
                    .flatMap((ranking) => ranking.hits)
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
                <More label="More result options">
                  <Disclosure id="search-diagnostics" className="diagnostics">
                    <summary>Snapshot and search diagnostics</summary>
                    <p>
                      Snapshot <code>{w.active.result.snapshot_id}</code>
                    </p>
                    <p>
                      All methods below use this same snapshot. Scores have
                      different meanings and are not a shared scale.
                    </p>
                    <pre>
                      {JSON.stringify(
                        Object.fromEntries(
                          Object.entries(w.active.result.results).map(
                            ([method, ranking]) => [
                              method,
                              ranking.configuration,
                            ],
                          ),
                        ),
                        null,
                        2,
                      )}
                    </pre>
                  </Disclosure>
                </More>
              </>
            )}
          </div>
          <div className="workbench-results" aria-busy={w.busy || undefined}>
            {!collection.active_snapshot ? (
              <EmptyState title="Add sources to search this collection">
                Open Sources and add text documents or PDFs. Search becomes
                available after processing finishes.
              </EmptyState>
            ) : w.busy && !w.active ? (
              <div
                className="passage-skeletons"
                role="region"
                aria-label="Loading passages"
              >
                {[0, 1, 2].map((index) => (
                  <PassageSkeleton key={index} />
                ))}
              </div>
            ) : !w.active ? (
              <EmptyState
                title={
                  w.error
                    ? "Search is unavailable"
                    : "Your passages will appear here"
                }
              >
                {w.error
                  ? "Use Retry search above, or check the connection and search again."
                  : "Enter a question and choose Sparse, Dense, or Hybrid to begin reading."}
              </EmptyState>
            ) : !w.visible.length ? (
              <EmptyState
                title={
                  w.filter || w.methodFilter !== "active"
                    ? "No returned passages match"
                    : "No passages found"
                }
              >
                {w.filter || w.methodFilter !== "active" ? (
                  <>
                    Clear the filter or try a different title or phrase.{" "}
                    <Button
                      onClick={() => {
                        w.setFilter("");
                        w.setMethodFilter("active");
                      }}
                    >
                      Clear filters
                    </Button>
                  </>
                ) : (
                  "No matching passages. Try a different question."
                )}
              </EmptyState>
            ) : (
              <div
                role="region"
                aria-label={`${methodNames[w.displayMethod]} · ${methodDetails[w.displayMethod]}`}
              >
                <ol
                  ref={cards}
                  className={compact ? "passage-list compact" : "passage-list"}
                >
                  {w.visible.map((passage) => (
                    <li
                      key={passageIdentity(
                        w.active!.result.snapshot_id,
                        passage.hit.chunk_id,
                      )}
                      value={passage.ranks[passage.method]?.rank}
                    >
                      <PassageCard
                        passage={passage}
                        snapshot={w.active!.result.snapshot_id}
                        query={w.active!.spec.query}
                        selected={w.selected?.chunk_id === passage.hit.chunk_id}
                        shortlisted={w.shortlist.some(
                          (item) =>
                            passageIdentity(
                              item.snapshot_id,
                              item.hit.chunk_id,
                            ) ===
                            passageIdentity(
                              w.active!.result.snapshot_id,
                              passage.hit.chunk_id,
                            ),
                        )}
                        onShortlist={() => w.toggle(passage)}
                        onInspect={(trigger) => inspect(passage.hit, trigger)}
                        onCopy={() =>
                          void w.copy(
                            passage.hit,
                            w.active!.result.snapshot_id,
                            w.active!.spec.query,
                          )
                        }
                      />
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
        <aside className="atlas-slot" aria-label="Evidence Atlas panel">
          <Disclosure>
            <summary>
              <Map size={18} aria-hidden="true" />
              Evidence Atlas
            </summary>
            <AtlasPanel
              selectedPassageId={w.selected?.chunk_id ?? null}
              highlights={highlights}
            />
          </Disclosure>
        </aside>
      </div>
      <CompareDrawer
        open={comparisonOpen}
        items={w.shortlist}
        onClose={() => setComparisonOpen(false)}
        onRemove={w.remove}
        onExport={w.exportShortlist}
      />
      {w.selected && w.active && (
        <SearchInspector
          key={`${w.active.result.snapshot_id}:${w.selected.chunk_id}`}
          hit={w.selected}
          snapshot={w.active.result.snapshot_id}
          collectionId={collection.collection_id}
          onClose={() => {
            w.setSelected(null);
            inspectorTrigger.current?.focus();
          }}
        />
      )}
    </section>
  );
}
