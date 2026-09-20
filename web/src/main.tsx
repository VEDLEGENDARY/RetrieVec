import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, APIError, type Collection, type Session } from "./api";
import "./style.css";
import { Uploads } from "./Uploads";
import { Search } from "./Search";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selected, setSelected] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const active = collections.find((item) => item.collection_id === selected);
  const fail = useCallback((error: unknown) => {
    if (error instanceof APIError && error.status === 401) {
      setSession(null);
      setCollections([]);
      setSelected("");
    }
    if (error instanceof APIError && error.status === 404) {
      setSelected("");
      setCollections([]);
    }
    setError(
      error instanceof Error ? error.message : "Request failed. Try again.",
    );
  }, []);
  const refresh = useCallback(async () => {
    const values = await api<Collection[]>("/api/v1/collections");
    setCollections(values);
    setSelected((current) =>
      values.some((item) => item.collection_id === current)
        ? current
        : (values[0]?.collection_id ?? ""),
    );
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    api<Session>("/api/v1/me", { signal: controller.signal })
      .then((value) => {
        setSession(value);
        return refresh();
      })
      .catch((error) => {
        if (error.name !== "AbortError" && error.status !== 401) fail(error);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [refresh, fail]);
  async function create(event: React.SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<Collection>(
        "/api/v1/collections",
        { method: "POST", body: JSON.stringify({ title }) },
        session?.csrf_token,
      );
      setTitle("");
      await refresh();
      setSelected(result.collection_id);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function archive() {
    if (
      !active ||
      !window.confirm(
        `Archive “${active.title}”? Access and pending processing will stop. Retained files are not erased.`,
      )
    )
      return;
    setBusy(true);
    try {
      await api(
        `/api/v1/collections/${active.collection_id}`,
        { method: "DELETE" },
        session?.csrf_token,
      );
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" }, session?.csrf_token);
      setSession(null);
      setCollections([]);
      setSelected("");
    } catch (error) {
      fail(error);
    }
  }
  if (loading)
    return (
      <main className="welcome">
        <p role="status">Opening your workspace…</p>
      </main>
    );
  if (!session)
    return (
      <main className="welcome">
        <div className="wordmark">
          R<span>↗</span> RetrieVec
        </div>
        <p className="eyebrow">YOUR PAPERS. TRACEABLE EVIDENCE.</p>
        <h1>
          Research begins
          <br />
          with the source.
        </h1>
        <p className="intro">
          A private workspace to collect papers, compare retrieval methods, and
          inspect the evidence behind every result.
        </p>
        <a className="button primary" href="/auth/login">
          Sign in to your workspace →
        </a>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <p className="muted">
          Private collections · Snapshot-pinned search · Original sources
        </p>
      </main>
    );
  return (
    <div className="workspace">
      <a className="skip" href="#research">
        Skip to research
      </a>
      <aside className="navigation">
        <div className="wordmark">
          R<span>↗</span> RetrieVec
        </div>
        <p className="eyebrow">COLLECTIONS</p>
        <nav aria-label="Collections">
          {collections.map((item) => (
            <button
              key={item.collection_id}
              className={
                selected === item.collection_id
                  ? "collection selected"
                  : "collection"
              }
              aria-pressed={selected === item.collection_id}
              onClick={() => {
                setSelected(item.collection_id);
                setError("");
              }}
            >
              <span>{item.title}</span>
              <small>
                {item.visibility === "curated" ? "Curated" : "Private"}
              </small>
            </button>
          ))}
        </nav>
        <form onSubmit={create} className="new-collection">
          <label htmlFor="collection-title">New collection</label>
          <input
            id="collection-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={120}
            required
            placeholder="e.g. Retrieval methods"
          />
          <button disabled={busy || !title.trim()} type="submit">
            + Create collection
          </button>
        </form>
        <div className="account">
          <span>Private workspace</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main id="research" className="research">
        <header>
          <div>
            <p className="eyebrow">RESEARCH WORKSPACE</p>
            <h1>{active?.title ?? "A place for your next question"}</h1>
          </div>
          {active?.can_manage && (
            <button className="quiet" onClick={archive} disabled={busy}>
              Archive collection
            </button>
          )}
        </header>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {active && (
          <Uploads
            key={active.collection_id}
            collection={active}
            session={session}
            refresh={refresh}
            fail={fail}
          />
        )}
        {active && (
          <Search
            key={`search-${active.collection_id}`}
            collection={active}
            session={session}
            fail={fail}
          />
        )}
        {!active ? (
          <section className="empty">
            <span className="empty-symbol">＋</span>
            <h2>Start with a collection</h2>
            <p>
              Give your research a home. Create a private collection, then add
              your source documents.
            </p>
          </section>
        ) : null}
        <footer>
          Paper evidence and RetrieVec measurements are distinct. Retrieval
          scores measure ranking, not scientific validity.
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
