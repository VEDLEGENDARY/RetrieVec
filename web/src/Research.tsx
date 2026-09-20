import { useCallback, useEffect, useState } from "react";
import { api, type Collection, type Session } from "./api";

type Conversation = { conversation_id: string; title: string };
type Provider = {
  name: string;
  model: string;
  cloud: boolean;
  consented: boolean;
};
type Evidence = {
  evidence_id: string;
  citation_id: string;
  title: string;
  text: string;
  page_range: number[] | null;
  source_id: string | null;
  snapshot_id?: string;
};
type Claim = { id: string; text: string; evidence_ids: string[] };
type Comparison = {
  method: string;
  dataset: string;
  metric: string;
  reported_value: string;
  experimental_conditions: string;
  limitations: string;
  evidence_ids: string[];
  comparability_note: string;
};
type Run = {
  run_id: string;
  conversation_id: string;
  original_question: string;
  effective_query: string;
  snapshot_id: string;
  state: string;
  error_code: string | null;
  configuration: {
    provider: string;
    retrieval: string;
    generation: { model: string; revision: string };
  };
  result: null | {
    answer: {
      status: string;
      claims: Claim[];
      comparisons: Comparison[];
      limitations: string[];
    };
    evidence: Evidence[];
    elapsed_ms: number;
    budget: { excluded: unknown[]; input_tokens: number };
  };
};
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
    "The provider failed or exceeded its budget. Search is still available. A remote request may have been billed.",
  invalid_answer:
    "The answer failed citation or structure checks. No unverified answer was published.",
  retrieval_unavailable:
    "The pinned retrieval snapshot or search service is unavailable.",
  source_unavailable: "Retained evidence or an original source is unavailable.",
  worker_interrupted:
    "The worker stopped before confirming completion. Retry creates a new run; remote billing may be uncertain.",
};

export function Research({
  collection,
  session,
  fail,
}: {
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversation, setConversation] = useState("");
  const [history, setHistory] = useState<Run[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState("");
  const [question, setQuestion] = useState("");
  const [effective, setEffective] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [requestKey, setRequestKey] = useState(() => crypto.randomUUID());
  const selectedProvider = providers.find((item) => item.name === provider);
  const refreshProviders = useCallback(async () => {
    const rows = await api<Provider[]>(
      `/api/v1/collections/${collection.collection_id}/providers`,
    );
    setProviders(rows);
    setProvider((current) =>
      rows.some((item) => item.name === current)
        ? current
        : (rows[0]?.name ?? ""),
    );
  }, [collection.collection_id]);
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
    refreshProviders().catch(fail);
    return () => controller.abort();
  }, [collection.collection_id, refreshProviders, fail]);
  useEffect(() => {
    if (!conversation) {
      setHistory([]);
      return;
    }
    const controller = new AbortController();
    api<Run[]>(`/api/v1/conversations/${conversation}/runs`, {
      signal: controller.signal,
    })
      .then(setHistory)
      .catch((error) => {
        if (error.name !== "AbortError") fail(error);
      });
    return () => controller.abort();
  }, [conversation, run?.state, fail]);
  const runId = run?.run_id;
  useEffect(() => {
    if (!runId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const current = await api<Run>(`/api/v1/runs/${runId}`, {
          signal: controller.signal,
        });
        setRun(current);
        timer = setTimeout(
          refresh,
          activeStates.has(current.state) ? 1200 : 5000,
        );
      } catch (error) {
        if (!controller.signal.aborted) {
          setRun(null);
          setEvidence(null);
          fail(error);
        }
      }
    }
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [runId, fail]);

  async function submit(
    snapshot: "current" | "historical" = "current",
    replay = false,
  ) {
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
            parent_run: run?.run_id ?? null,
            snapshot,
          }),
        },
        session.csrf_token,
      );
      setRun(created);
      setRequestKey(crypto.randomUUID());
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function inspect(item: Evidence) {
    try {
      setEvidence(await api<Evidence>(`/api/v1/citations/${item.citation_id}`));
    } catch (error) {
      setEvidence(null);
      fail(error);
    }
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
      return item ? (
        <button
          className="quiet citation"
          key={id}
          onClick={() => inspect(item)}
          aria-label={`Inspect citation ${id}`}
        >
          {item.title}
        </button>
      ) : null;
    });
  return (
    <section className="saved-research" aria-labelledby="saved-title">
      <p className="eyebrow">SAVED RESEARCH</p>
      <h2 id="saved-title">Ask the evidence</h2>
      <p className="muted">
        Answers stay tied to their sources. Structural checks do not establish
        scientific or semantic correctness.
      </p>
      <label htmlFor="conversation">Conversation</label>
      <select
        id="conversation"
        value={conversation}
        onChange={(event) => {
          setConversation(event.target.value);
          setRun(null);
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
      </select>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="research-question">Research question</label>
        <textarea
          id="research-question"
          value={question}
          maxLength={4096}
          required
          rows={3}
          onChange={(event) => {
            setQuestion(event.target.value);
            setRequestKey(crypto.randomUUID());
          }}
        />
        <label htmlFor="effective-query">
          Standalone query for a follow-up (optional)
        </label>
        <input
          id="effective-query"
          value={effective}
          maxLength={4096}
          onChange={(event) => {
            setEffective(event.target.value);
            setRequestKey(crypto.randomUUID());
          }}
          placeholder="Include the method or paper your follow-up refers to"
        />
        <label htmlFor="generation-provider">Generation provider</label>
        <select
          id="generation-provider"
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
        </select>
        <button
          className="primary"
          disabled={
            busy ||
            !question.trim() ||
            !collection.active_snapshot ||
            !selectedProvider?.consented
          }
        >
          Generate cited answer
        </button>
      </form>
      {!collection.active_snapshot && (
        <p>Upload and process a source before creating a research run.</p>
      )}
      {!providers.length && (
        <p>
          Generation is not configured. You can continue searching and
          inspecting sources above.
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
            <button onClick={() => consent(!selectedProvider.consented)}>
              {selectedProvider.consented
                ? "Revoke cloud consent"
                : "Allow this cloud provider"}
            </button>
          ) : (
            <p>The collection owner manages cloud consent.</p>
          )}
        </div>
      )}
      {!!history.length && (
        <nav aria-label="Saved research runs" className="run-history">
          {history.map((item) => (
            <button
              key={item.run_id}
              aria-pressed={run?.run_id === item.run_id}
              onClick={() => {
                setRun(item);
                setEvidence(null);
              }}
            >
              {item.original_question} · {item.state}
            </button>
          ))}
        </nav>
      )}
      {run && (
        <article className="answer">
          <h3>{run.original_question}</h3>
          <p role="status">Research run: {run.state}</p>
          {activeStates.has(run.state) && (
            <button
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
            </button>
          )}
          {run.state === "failed" && (
            <p role="alert">
              {failure[run.error_code ?? ""] ??
                "Run failed. Check the services and retry."}
            </p>
          )}
          {run.state === "cancelled" && (
            <p>This run was cancelled. No late answer will be published.</p>
          )}
          {run.result && (
            <>
              <p className="answer-status">
                {run.result.answer.status.replaceAll("_", " ")}
              </p>
              {run.result.answer.claims.map((claim) => (
                <div className="claim" key={claim.id}>
                  <p>{claim.text}</p>
                  <div>{cite(claim.evidence_ids)}</div>
                </div>
              ))}
              {run.result.answer.comparisons.map((row, index) => (
                <section key={index} className="comparison">
                  <h4>{row.method}</h4>
                  <dl>
                    <dt>Dataset / metric</dt>
                    <dd>
                      {row.dataset} / {row.metric}
                    </dd>
                    <dt>Paper-reported value</dt>
                    <dd>{row.reported_value}</dd>
                    <dt>Conditions</dt>
                    <dd>{row.experimental_conditions}</dd>
                    <dt>Comparability</dt>
                    <dd>{row.comparability_note}</dd>
                    <dt>Limitations</dt>
                    <dd>{row.limitations}</dd>
                  </dl>
                  {cite(row.evidence_ids)}
                </section>
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
              <div className="export-actions">
                {["markdown", "bibtex", "json", "csv"].map((format) => (
                  <button key={format} onClick={() => exportRun(format)}>
                    Export {format}
                  </button>
                ))}
              </div>
            </>
          )}
          {!activeStates.has(run.state) && (
            <div className="replay-actions">
              <button
                disabled={busy}
                onClick={() => submit("historical", true)}
              >
                Replay pinned snapshot
              </button>
              <button disabled={busy} onClick={() => submit("current", true)}>
                Replay current snapshot
              </button>
            </div>
          )}
          <details>
            <summary>Run provenance</summary>
            <dl>
              <dt>Effective query</dt>
              <dd>{run.effective_query}</dd>
              <dt>Snapshot</dt>
              <dd>{run.snapshot_id}</dd>
              <dt>Model revision</dt>
              <dd>{run.configuration.generation.revision}</dd>
            </dl>
          </details>
        </article>
      )}
      {evidence && (
        <aside className="citation-inspector" aria-label="Citation evidence">
          <button onClick={() => setEvidence(null)}>Close citation</button>
          <h3>{evidence.title}</h3>
          <p>
            {evidence.page_range
              ? `Pages ${evidence.page_range.join("–")}`
              : "Page locator unavailable"}
          </p>
          <blockquote>{evidence.text}</blockquote>
          {evidence.source_id ? (
            <a
              target="_blank"
              rel="noreferrer"
              href={`/api/v1/sources/${evidence.source_id}?snapshot_id=${evidence.snapshot_id}#page=${evidence.page_range?.[0] ?? 1}`}
            >
              Open original source
            </a>
          ) : (
            <p>Exact passage retained; uploaded original unavailable.</p>
          )}
        </aside>
      )}
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
