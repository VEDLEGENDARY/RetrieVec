import { BasedOn } from "./BasedOn";
import { SectionField } from "./SectionField";
import { PaperDetails } from "./PaperDetails";
import { PassageLocation } from "./PassageLocation";
import { stateLabel, exportLabels, errorMessage } from "./presentation";
import {
  Button,
  ActionLink,
  Field,
  Input,
  Select,
  Textarea,
  Notice,
  StatusBadge,
  LoadingState,
  Disclosure,
  More,
} from "./ui";
import { Citation } from "./Citation";
import type {
  Conversation,
  SavedRun,
  Provider,
  Evidence,
  Run,
} from "./researchTypes";
import { EvidencePanel } from "./EvidencePanel";
import { useDraft } from "./drafts";
import { useRunProgress } from "./useRunProgress";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, APIError, type Collection, type Session } from "./api";
import { AdvancedEvidence } from "./AdvancedEvidence";
import { navigate } from "./routing";

const activeStates = new Set([
  "queued",
  "retrieving",
  "generating",
  "validating",
]);
const failure: Record<string, string> = {
  provider_unavailable:
    "The configured model is unavailable or changed. Check the provider setup, then retry.",
  provider_failed:
    "The provider failed or exceeded its budget. Search is still available. A remote request may have been billed. Check the provider before starting another run.",
  invalid_answer:
    "The answer failed citation or structure checks. No unverified answer was published. Review the passages or try a more focused question.",
  retrieval_unavailable:
    "The pinned retrieval snapshot or search service is unavailable. Contact the workspace operator before retrying.",
  source_unavailable:
    "Retained evidence or an original source is unavailable. Inspect the available passages or contact the collection owner.",
  worker_interrupted:
    "The worker stopped before confirming completion. Retry creates a new run; remote billing may be uncertain.",
};

export function Research({
  collection,
  session,
  fail,
  showHistory = false,
  linkedRun = "",
  providers,
  provider,
  setProvider,
  refreshProviders,
}: {
  providers: Provider[];
  provider: string;
  setProvider: (name: string) => void;
  refreshProviders: () => Promise<void>;
  showHistory?: boolean;
  linkedRun?: string;
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversation, setConversation] = useState("");
  const [history, setHistory] = useState<Run[]>([]);
  const [saved, setSaved] = useState<SavedRun[]>([]);
  const [savedQuery, setSavedQuery] = useState("");
  const [savedCursor, setSavedCursor] = useState<string | null>(null);
  const [savedPage, setSavedPage] = useState<string | null>(null);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savedError, setSavedError] = useState("");
  useEffect(() => {
    if (!showHistory) return;
    const controller = new AbortController();
    setSavedLoading(true);
    setSavedError("");
    const params = new URLSearchParams({ q: savedQuery });
    if (savedPage) params.set("before", savedPage);
    const timer = setTimeout(() => {
      api<{ items: SavedRun[]; next_cursor: string | null }>(
        `/api/v1/collections/${collection.collection_id}/runs?${params}`,
        { signal: controller.signal },
      )
        .then((value) => {
          if (!controller.signal.aborted) {
            setSaved(value.items);
            setSavedCursor(value.next_cursor);
          }
        })
        .catch((error) => {
          if (!controller.signal.aborted) {
            setSaved([]);
            setSavedCursor(null);
            setSavedError(
              "Saved research could not be loaded. Reopen Saved research to retry.",
            );
            fail(error);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setSavedLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [showHistory, collection.collection_id, savedQuery, savedPage, fail]);
  const [question, setQuestion, draftSaved] = useDraft(
    session.principal_id,
    collection.collection_id,
    "question",
  );
  const [effective, setEffective] = useDraft(
    session.principal_id,
    collection.collection_id,
    "follow-up",
  );
  const [run, setRun] = useState<Run | null>(null);
  const [selectedRunId, setRunSelection] = useState<string | null>(
    linkedRun || null,
  );
  function setSelectedRunId(run: string | null) {
    setRunSelection(run);
    navigate({ collection: collection.collection_id, run: run ?? "" });
  }
  useEffect(() => {
    setRunSelection(linkedRun || null);
    setRun(null);
    setEvidence(null);
  }, [linkedRun]);
  const [runRefresh, setRunRefresh] = useState(0);
  const refreshFromEvent = useCallback(
    () => setRunRefresh((value) => value + 1),
    [],
  );
  const progress = useRunProgress(
    run?.run_id ?? null,
    Boolean(run && activeStates.has(run.state)),
    refreshFromEvent,
  );
  const [runConnection, setRunConnection] = useState<
    "connected" | "retrying" | "offline"
  >("connected");
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const citationTrigger = useRef<HTMLButtonElement | null>(null);
  const inspectionVersion = useRef(0);
  useEffect(
    () => () => {
      inspectionVersion.current += 1;
    },
    [],
  );
  const [busy, setBusy] = useState(false);
  const [section, setSection] = useState("");
  const [notice, setNotice] = useState("");
  const [requestKey, setRequestKey] = useState(() => crypto.randomUUID());
  const selectedProvider = providers.find((item) => item.name === provider);
  const [rewritePreview, setRewritePreview] = useState("");
  const [rewriteError, setRewriteError] = useState("");
  useEffect(() => {
    setRewritePreview("");
    setRewriteError("");
    if (
      !run?.run_id ||
      !question.trim() ||
      effective ||
      !selectedProvider?.consented
    )
      return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api<{ effective_query: string }>(
        `/api/v1/runs/${run.run_id}/rewrite`,
        {
          method: "POST",
          signal: controller.signal,
          body: JSON.stringify({ question, provider }),
        },
        session.csrf_token,
      )
        .then((value) => {
          if (!controller.signal.aborted)
            setRewritePreview(value.effective_query);
        })
        .catch((error) => {
          if (!controller.signal.aborted) setRewriteError(errorMessage(error));
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [
    run?.run_id,
    question,
    effective,
    provider,
    selectedProvider?.consented,
    session.csrf_token,
  ]);
  useEffect(() => {
    const controller = new AbortController();
    api<Conversation[]>(
      `/api/v1/collections/${collection.collection_id}/conversations`,
      { signal: controller.signal },
    )
      .then(setConversations)
      .catch((error) => {
        if (error.name !== "AbortError") fail(error);
      });
    return () => controller.abort();
  }, [collection.collection_id, fail]);
  useEffect(() => {
    if (!conversation) {
      setHistory([]);
      return;
    }
    const controller = new AbortController();
    api<Run[]>(`/api/v1/conversations/${conversation}/runs`, {
      signal: controller.signal,
    })
      .then((rows) => {
        if (!controller.signal.aborted) setHistory(rows);
      })
      .catch((error) => {
        if (error.name !== "AbortError") fail(error);
      });
    return () => controller.abort();
  }, [conversation, run?.state, fail]);
  const runId = selectedRunId;
  useEffect(() => {
    if (!runId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    async function refresh() {
      try {
        const current = await api<Run>(`/api/v1/runs/${runId}`, {
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(15000),
          ]),
        });
        if (controller.signal.aborted) return;
        failures = 0;
        setRunConnection("connected");
        setRun(current);
        setConversation(current.conversation_id);
        timer = setTimeout(
          refresh,
          activeStates.has(current.state) ? 1200 : 5000,
        );
      } catch (error) {
        if (!controller.signal.aborted) {
          inspectionVersion.current += 1;
          setRun(null);
          setEvidence(null);
          if (
            error instanceof APIError &&
            error.status < 500 &&
            error.status !== 429
          ) {
            setSelectedRunId(null);
            setRunConnection("connected");
            fail(error);
          } else {
            failures += 1;
            setRunConnection(failures <= 4 ? "retrying" : "offline");
            if (failures <= 4)
              timer = setTimeout(
                refresh,
                Math.min(15000, 1000 * 2 ** failures),
              );
          }
        }
      }
    }
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [runId, runRefresh, fail]);

  async function submit(
    snapshot: "current" | "historical" = "current",
    replay = false,
  ) {
    if (
      busy ||
      (!replay &&
        (!question.trim() ||
          !collection.active_snapshot ||
          !selectedProvider?.consented))
    )
      return;
    inspectionVersion.current += 1;
    setBusy(true);
    setNotice("");
    setEvidence(null);
    try {
      let id = conversation;
      if (!id) {
        const created = await api<Conversation>(
          "/api/v1/conversations",
          {
            method: "POST",
            body: JSON.stringify({
              collection_id: collection.collection_id,
              title: question.slice(0, 120),
            }),
          },
          session.csrf_token,
        );
        id = created.conversation_id;
        setConversation(id);
        setConversations((rows) => [created, ...rows]);
      }
      const created = await api<Run>(
        `/api/v1/conversations/${id}/runs`,
        {
          method: "POST",
          headers: {
            "Idempotency-Key": replay ? crypto.randomUUID() : requestKey,
          },
          body: JSON.stringify({
            question: replay && run ? run.original_question : question,
            effective_query:
              replay && run ? run.effective_query : effective || null,
            provider: replay && run ? run.configuration.provider : provider,
            retrieval: replay && run ? run.configuration.retrieval : "hybrid",
            section:
              replay && run
                ? (run.configuration.section ?? null)
                : section || null,
            parent_run: run?.run_id ?? null,
            snapshot,
          }),
        },
        session.csrf_token,
      );
      setRun(created);
      setSelectedRunId(created.run_id);
      setRunConnection("connected");
      setRequestKey(crypto.randomUUID());
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function inspect(item: Evidence, trigger: HTMLButtonElement) {
    const version = ++inspectionVersion.current;
    citationTrigger.current = trigger;
    try {
      const value = await api<Evidence>(
        `/api/v1/citations/${item.citation_id}`,
      );
      if (version === inspectionVersion.current) setEvidence(value);
    } catch (error) {
      if (version !== inspectionVersion.current) return;
      setEvidence(null);
      fail(error);
    }
  }
  function closeCitation() {
    inspectionVersion.current += 1;
    setEvidence(null);
    citationTrigger.current?.focus();
  }
  async function exportRun(format: string) {
    if (!run) return;
    try {
      const result = await api<{ download_url: string }>(
        `/api/v1/runs/${run.run_id}/exports`,
        { method: "POST", body: JSON.stringify({ format }) },
        session.csrf_token,
      );
      const response = await fetch(result.download_url, {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok)
        throw new Error(
          "Download expired or access changed. Create a new export.",
        );
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `research-${run.run_id}.${({ markdown: "md", bibtex: "bib" } as Record<string, string>)[format] ?? format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice("Export downloaded from this saved run.");
    } catch (error) {
      fail(error);
    }
  }
  async function consent(enable: boolean) {
    try {
      await api(
        `/api/v1/collections/${collection.collection_id}/providers/${provider}/consent`,
        { method: enable ? "PUT" : "DELETE" },
        session.csrf_token,
      );
      await refreshProviders();
    } catch (error) {
      fail(error);
    }
  }
  const cite = (ids: string[]) =>
    ids.map((id) => {
      const item = run?.result?.evidence.find(
        (value) => value.evidence_id === id,
      );
      return item ? <Citation key={id} item={item} inspect={inspect} /> : null;
    });
  return (
    <section className="saved-research" aria-labelledby="saved-title">
      <h2 id="saved-title">
        {showHistory ? "Saved research" : "Cited answers"}
      </h2>
      <p className="muted">
        Answers stay tied to their sources. Structural checks do not establish
        scientific or semantic correctness.
      </p>
      <div hidden={!showHistory}>
        <Field label="Find saved research">
          <Input
            id="saved-search"
            type="search"
            maxLength={256}
            value={savedQuery}
            onChange={(event) => {
              setSavedQuery(event.target.value);
              setSavedPage(null);
              setSaved([]);
            }}
          />
        </Field>
        {savedLoading ? (
          <LoadingState label="Loading saved research…" />
        ) : savedError ? (
          <Notice error>{savedError}</Notice>
        ) : (
          <nav aria-label="All saved research">
            {saved.map((item) => (
              <Button
                key={item.run_id}
                onClick={() => {
                  setConversation(item.conversation_id);
                  setRun(null);
                  setEvidence(null);
                  inspectionVersion.current += 1;
                  setSelectedRunId(item.run_id);
                  setRunRefresh((value) => value + 1);
                }}
              >
                {item.original_question}
                <small>
                  {stateLabel(item.state)} ·{" "}
                  {new Date(item.created_at).toLocaleDateString()}
                </small>
              </Button>
            ))}
            {saved.length === 0 && (
              <p>
                No saved research matches. Ask a question to start a saved run.
              </p>
            )}
          </nav>
        )}
        {savedPage && (
          <Button onClick={() => setSavedPage(null)}>Newest research</Button>
        )}
        {savedCursor && (
          <Button
            disabled={savedLoading}
            onClick={() => setSavedPage(savedCursor)}
          >
            Older research
          </Button>
        )}
        <More label="Browse conversations">
          <Field label="Conversation">
            <Select
              id="conversation"
              disabled={busy}
              value={conversation}
              onChange={(event) => {
                inspectionVersion.current += 1;
                setConversation(event.target.value);
                setRun(null);
                setSelectedRunId(null);
                setRunConnection("connected");
                setEvidence(null);
                setRequestKey(crypto.randomUUID());
              }}
            >
              <option value="">New conversation</option>
              {conversations.map((item) => (
                <option key={item.conversation_id} value={item.conversation_id}>
                  {item.title}
                </option>
              ))}
            </Select>
          </Field>
        </More>
      </div>
      <form
        hidden={showHistory}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <Field label="Question for cited answer">
          <Textarea
            id="research-question"
            disabled={busy}
            value={question}
            maxLength={4096}
            required
            rows={3}
            onKeyDown={(event) => {
              if (
                (event.ctrlKey || event.metaKey) &&
                event.key === "Enter" &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            onChange={(event) => {
              setQuestion(event.target.value);
              setRequestKey(crypto.randomUUID());
            }}
          />
        </Field>
        <p className="muted">
          {draftSaved
            ? "Draft saved on this device for 7 days. Cleared on sign out."
            : "Device storage is unavailable. Keep this tab open to retain your draft."}
        </p>
        <p>
          Searching for:{" "}
          {effective || rewritePreview || question || "Enter a question"}
          <Button
            type="button"
            className="quiet"
            onClick={() => {
              setEffective(effective || rewritePreview || question);
              const input = document.getElementById(
                "effective-query",
              ) as HTMLInputElement | null;
              const details = input?.closest("details");
              if (details) details.open = true;
              input?.focus();
            }}
          >
            Edit search query
          </Button>
        </p>
        {rewriteError && <Notice error>{rewriteError}</Notice>}
        <More label="More answer options">
          <SectionField
            value={section}
            disabled={busy}
            onChange={(value) => {
              setSection(value);
              setRequestKey(crypto.randomUUID());
            }}
          />
          <Field label="Standalone query for a follow-up (optional)">
            <Input
              id="effective-query"
              disabled={busy}
              value={effective}
              maxLength={4096}
              onChange={(event) => {
                setEffective(event.target.value);
                setRequestKey(crypto.randomUUID());
              }}
              placeholder="Include the method or paper your follow-up refers to"
            />
          </Field>
          <Field label="Generation provider">
            <Select
              id="generation-provider"
              disabled={busy}
              value={provider}
              onChange={(event) => {
                setProvider(event.target.value);
                setRequestKey(crypto.randomUUID());
              }}
            >
              {!providers.length && (
                <option value="">No provider configured</option>
              )}
              {providers.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.model} · {item.cloud ? "Cloud" : "Local"}
                </option>
              ))}
            </Select>
          </Field>
        </More>
        <p className="muted">
          {selectedProvider
            ? `${selectedProvider.model} · ${selectedProvider.cloud ? "Cloud" : "Local"}`
            : "No answer provider configured. Use Find passages to search your sources."}
        </p>
        <Button
          className="primary"
          title="Generate cited answer (Ctrl or Command + Enter)"
          aria-keyshortcuts="Control+Enter Meta+Enter"
          disabled={
            busy ||
            !question.trim() ||
            !collection.active_snapshot ||
            !selectedProvider?.consented
          }
        >
          Generate cited answer
        </Button>
      </form>
      {!collection.active_snapshot && (
        <p>Upload and process a source before creating a research run.</p>
      )}
      {!providers.length && (
        <p>
          Generation is not configured. You can continue searching and
          inspecting sources in Find passages.
        </p>
      )}
      {selectedProvider?.cloud && (
        <div className="consent">
          <p>
            Using this cloud provider sends the question and selected passages
            outside this computer. Consent applies to this collection and
            provider configuration.
          </p>
          {collection.can_manage ? (
            <Button onClick={() => consent(!selectedProvider.consented)}>
              {selectedProvider.consented
                ? "Revoke cloud consent"
                : "Allow this cloud provider"}
            </Button>
          ) : (
            <p>The collection owner manages cloud consent.</p>
          )}
        </div>
      )}
      {showHistory && !!history.length && (
        <nav aria-label="Saved research runs" className="run-history">
          {history.map((item) => (
            <Button
              key={item.run_id}
              disabled={busy}
              aria-pressed={selectedRunId === item.run_id}
              onClick={() => {
                inspectionVersion.current += 1;
                // Reauthorize history before showing a cached answer or enabling exports.
                setRun(null);
                setSelectedRunId(item.run_id);
                setRunRefresh((value) => value + 1);
                setRunConnection("retrying");
                setEvidence(null);
              }}
            >
              {item.original_question} · {stateLabel(item.state)}
            </Button>
          ))}
        </nav>
      )}
      {selectedRunId && runConnection !== "connected" && (
        <div role="status">
          <p>
            {runConnection === "retrying"
              ? "Reconnecting to the saved run. Evidence is hidden until access is confirmed."
              : "The saved run is unavailable right now. Retry when the service is available."}
          </p>
          {runConnection === "offline" && (
            <Button
              type="button"
              onClick={() => {
                setRunConnection("retrying");
                setRunRefresh((value) => value + 1);
              }}
            >
              Reconnect to saved run
            </Button>
          )}
        </div>
      )}
      {run && (
        <article className="answer">
          <h3>{run.original_question}</h3>
          <p role="status">Research run: {stateLabel(run.state)}</p>
          {activeStates.has(run.state) && (
            <LoadingState
              label={
                run.state === "retrieving"
                  ? "Finding relevant passages…"
                  : run.state === "validating"
                    ? "Checking citations and source integrity…"
                    : run.state === "queued"
                      ? "Waiting for the research worker…"
                      : "Preparing your answer…"
              }
            />
          )}
          {activeStates.has(run.state) && progress.sources.length > 0 && (
            <More label={`${progress.sources.length} sources retrieved`} open>
              <p>
                Evidence selected from the pinned snapshot. The answer is still
                being generated and checked.
              </p>
              {progress.sources.map((source) => (
                <article key={source.evidence_id}>
                  <h4>{source.title}</h4>
                  <blockquote>{source.text}</blockquote>
                </article>
              ))}
            </More>
          )}
          {activeStates.has(run.state) && (
            <Button
              disabled={busy}
              onClick={async () => {
                try {
                  await api(
                    `/api/v1/runs/${run.run_id}/cancel`,
                    { method: "POST" },
                    session.csrf_token,
                  );
                } catch (error) {
                  fail(error);
                }
              }}
            >
              Cancel run
            </Button>
          )}
          {run.state === "failed" && (
            <Notice error>
              {failure[run.error_code ?? ""] ??
                "Run failed. Check the services and retry."}
            </Notice>
          )}
          {run.state === "cancelled" && (
            <p>This run was cancelled. No late answer will be published.</p>
          )}
          {run.result && (
            <>
              <BasedOn
                kind="answer"
                snapshot={run.snapshot_id}
                model={
                  run.configuration.generation.model +
                  " · " +
                  run.configuration.generation.revision
                }
                candidates={run.result.evidence.map((item) => ({
                  id: item.evidence_id,
                  content: cite([item.evidence_id]),
                }))}
                usedIds={[
                  ...run.result.answer.claims.flatMap(
                    (claim) => claim.evidence_ids,
                  ),
                  ...run.result.answer.comparisons.flatMap(
                    (row) => row.evidence_ids,
                  ),
                ]}
              />
              <StatusBadge className="answer-status">
                {run.result.answer.status === "insufficient_evidence"
                  ? "I could not find this in your papers."
                  : run.result.answer.status === "partial"
                    ? "The sources support only part of this answer."
                    : "Answer with cited evidence"}
              </StatusBadge>
              {run.result.answer.claims.map((claim) => (
                <div className="claim" key={claim.id}>
                  <p>{claim.text}</p>
                  <div>{cite(claim.evidence_ids)}</div>
                </div>
              ))}
              {run.result.answer.comparisons.map((row, index) => (
                <div key={index} className="advanced-table comparison">
                  <table>
                    <caption>Cited paper comparison {index + 1}</caption>
                    <tbody>
                      {[
                        ["Method", row.method],
                        ["Dataset / metric", `${row.dataset} / ${row.metric}`],
                        ["Paper-reported value", row.reported_value],
                        ["Conditions", row.experimental_conditions],
                        ["Comparability", row.comparability_note],
                        ["Limitations", row.limitations],
                      ].map(([label, value]) => (
                        <tr key={label}>
                          <th scope="row">{label}</th>
                          <td>
                            {value} {cite(row.evidence_ids)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              <ul>
                {run.result.answer.limitations.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
              <p className="muted">
                Structurally checked · Human review pending ·{" "}
                {Math.round(run.result.elapsed_ms)} ms
              </p>
              <More label="Export answer">
                <div className="export-actions">
                  {["markdown", "bibtex", "json", "csv"].map((format) => (
                    <Button
                      id={`run-export-${format}`}
                      key={format}
                      onClick={() => exportRun(format)}
                    >
                      Export {exportLabels[format] ?? format}
                    </Button>
                  ))}
                </div>
              </More>
            </>
          )}
          <More label="More run options">
            {!activeStates.has(run.state) && (
              <div className="replay-actions">
                <Button
                  id="replay-pinned"
                  disabled={busy}
                  onClick={() => submit("historical", true)}
                >
                  Replay pinned snapshot
                </Button>
                <Button
                  id="replay-current"
                  disabled={busy}
                  onClick={() => submit("current", true)}
                >
                  Replay current snapshot
                </Button>
              </div>
            )}
            <Disclosure id="run-provenance">
              <summary>Run provenance</summary>
              <dl>
                <dt>Effective query</dt>
                <dd>{run.effective_query}</dd>
                <dt>Snapshot</dt>
                <dd>{run.snapshot_id}</dd>
                <dt>Model revision</dt>
                <dd>{run.configuration.generation.revision}</dd>
              </dl>
            </Disclosure>
          </More>
        </article>
      )}
      {evidence && (
        <EvidencePanel
          title={evidence.title}
          text={evidence.text}
          pages={evidence.page_range}
          snapshot={evidence.snapshot_id ?? run?.snapshot_id ?? "Unavailable"}
          onClose={closeCitation}
        >
          <PaperDetails paper={evidence} />
          {!evidence.evidence_object_id && evidence.chunk_id && run && (
            <PassageLocation
              key={evidence.chunk_id}
              passage={evidence}
              collectionId={collection.collection_id}
              snapshotId={evidence.snapshot_id ?? run.snapshot_id}
              chunkId={evidence.chunk_id}
            />
          )}
          {evidence.evidence_object_id && evidence.chunk_id && run && (
            <AdvancedEvidence
              collectionId={collection.collection_id}
              snapshotId={run.snapshot_id}
              chunkId={evidence.chunk_id}
            />
          )}
          {evidence.source_id ? (
            <ActionLink
              target="_blank"
              rel="noreferrer"
              href={`/api/v1/sources/${evidence.source_id}?snapshot_id=${evidence.snapshot_id}#page=${evidence.page_range?.[0] ?? 1}`}
            >
              Open original source
            </ActionLink>
          ) : (
            <p>Exact passage retained; uploaded original unavailable.</p>
          )}
        </EvidencePanel>
      )}
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
