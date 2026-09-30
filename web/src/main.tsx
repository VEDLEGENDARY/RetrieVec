import { Button, Input, Skeleton } from "./ui";
import { useEffect, useState } from "react";
import { recordTiming } from "./performance";
import { createRoot } from "react-dom/client";
import { api, type Collection } from "./api";
import "./style.css";
import { Uploads } from "./Uploads";
import { Search } from "./Search";
import { Research } from "./Research";
import { CommandMenu } from "./CommandMenu";
import { useWorkspace } from "./useWorkspace";
import { NavigationPanel } from "./NavigationPanel";
import {
  Archive,
  ArrowUpRight,
  BookOpenText,
  FileText,
  LogOut,
  Menu,
  Plus,
  Search as SearchIcon,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type View = "ask" | "sources" | "saved";
const viewLabels: Record<View, string> = {
  ask: "Ask",
  sources: "Sources",
  saved: "Saved research",
};

function App() {
  const {
    session,
    loading,
    collections,
    selected,
    setSelected,
    error,
    setError,
    refresh,
    fail,
    logout,
  } = useWorkspace();
  const [title, setTitle] = useState("");
  useEffect(() => {
    if (!loading) recordTiming("app.ready", performance.now());
  }, [loading]);

  const [busy, setBusy] = useState(false);
  const [archived, setArchived] = useState<Collection | null>(null);
  useEffect(() => setArchived(null), [session?.principal_id]);
  const [view, setView] = useState<View>("ask");
  const [askMode, setAskMode] = useState<"passages" | "answer">("passages");
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [collectionFilter, setCollectionFilter] = useState("");
  const active = collections.find((item) => item.collection_id === selected);
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
      setView("ask");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function archive() {
    if (!active || busy) return;
    setBusy(true);
    setError("");
    try {
      await api(
        `/api/v1/collections/${active.collection_id}`,
        { method: "DELETE" },
        session?.csrf_token,
      );
      setArchived(active);
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function restoreArchived() {
    if (!archived || busy) return;
    setBusy(true);
    setError("");
    try {
      const restored = await api<Collection>(
        `/api/v1/collections/${archived.collection_id}/restore`,
        { method: "POST" },
        session?.csrf_token,
      );
      await refresh();
      setSelected(restored.collection_id);
      setView("sources");
      setArchived(null);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  if (loading)
    return (
      <main className="welcome">
        <Skeleton label="Opening your workspace…" />
      </main>
    );
  if (!session)
    return (
      <main className="welcome">
        <div className="wordmark">
          <span className="logo-mark">
            <BookOpenText size={19} />
          </span>{" "}
          RetrieVec
        </div>
        <p className="eyebrow">Your papers. Traceable evidence.</p>
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
          Sign in to your workspace <ArrowUpRight size={17} />
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
      <NavigationPanel
        open={navigationOpen}
        onClose={() => setNavigationOpen(false)}
      >
        <div className="wordmark">
          <span className="logo-mark">
            <BookOpenText size={18} />
          </span>{" "}
          RetrieVec
          <Button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setNavigationOpen(false)}
          >
            <X size={18} />
          </Button>
        </div>
        <p className="eyebrow">Collections</p>
        <label className="collection-filter">
          Find a collection
          <Input
            type="search"
            value={collectionFilter}
            onChange={(event) => setCollectionFilter(event.target.value)}
            placeholder="Filter collections…"
          />
        </label>
        <nav aria-label="Collections">
          {collections
            .filter((item) =>
              item.title.toLowerCase().includes(collectionFilter.toLowerCase()),
            )
            .map((item) => (
              <Button
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
                  setView("ask");
                  setNavigationOpen(false);
                }}
              >
                <span>{item.title}</span>
                <small>
                  {item.visibility === "curated" ? "Curated" : "Private"}
                </small>
              </Button>
            ))}
        </nav>
        {collectionFilter &&
          !collections.some((item) =>
            item.title.toLowerCase().includes(collectionFilter.toLowerCase()),
          ) && (
            <p className="muted" role="status">
              No collections match “{collectionFilter}”.
            </p>
          )}
        <form onSubmit={create} className="new-collection">
          <label htmlFor="collection-title">New collection</label>
          <Input
            id="collection-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={120}
            required
            placeholder="e.g. Retrieval methods"
          />
          <Button disabled={busy || !title.trim()} type="submit">
            <Plus size={16} /> Create collection
          </Button>
        </form>
        <div className="account">
          <span>
            <ShieldCheck size={14} /> Private workspace
          </span>
          <Button onClick={logout}>
            <LogOut size={14} /> Sign out
          </Button>
        </div>
      </NavigationPanel>
      <main id="research" className="research">
        <div className="workspace-toolbar">
          <span>Collection / {viewLabels[view]}</span>
          <CommandMenu
            actions={[
              ...(active
                ? [
                    {
                      id: "find-passages",
                      label: "Find passages",
                      detail: "Search evidence and compare retrieval methods",
                      run: () => {
                        setView("ask");
                        setAskMode("passages");
                      },
                    },
                    {
                      id: "answer",
                      label: "Answer a question",
                      detail: "Generate a cited answer",
                      run: () => {
                        setView("ask");
                        setAskMode("answer");
                      },
                    },
                  ]
                : []),
              ...(active ? (["ask", "sources", "saved"] as const) : []).map(
                (id) => ({
                  id,
                  label: viewLabels[id],
                  detail: active?.title ?? "Workspace",
                  run: () => setView(id),
                }),
              ),
              {
                id: "create",
                label: "Create a collection",
                detail: "Organize a new research topic",
                run: () => {
                  setNavigationOpen(true);
                  requestAnimationFrame(() =>
                    document.getElementById("collection-title")?.focus(),
                  );
                },
              },
              ...collections.map((item) => ({
                id: item.collection_id,
                label: item.title,
                detail: "Open collection",
                run: () => {
                  setSelected(item.collection_id);
                  setView("ask");
                  setError("");
                },
              })),
            ]}
          />
        </div>
        <header>
          <div>
            <Button
              className="mobile-menu"
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={navigationOpen}
              onClick={() => setNavigationOpen(true)}
            >
              <Menu size={19} />
            </Button>
            <p className="eyebrow">Research workspace</p>
            <h1>{active?.title ?? "A place for your next question"}</h1>
            {active && (
              <p className="header-meta">
                <ShieldCheck size={14} />{" "}
                {active.visibility === "curated"
                  ? "Curated collection"
                  : "Private collection"}
                <span />
                {active.active_snapshot ? "Search ready" : "Awaiting sources"}
              </p>
            )}
          </div>
          {active?.can_manage && (
            <Button
              className="quiet"
              onClick={archive}
              disabled={busy}
              title="Hide this collection and cancel active processing. Undo restores access, but does not restart cancelled work."
            >
              <Archive size={15} /> Archive collection
            </Button>
          )}
        </header>
        {archived && (
          <div className="notice" role="status">
            <p>
              “{archived.title}” archived. Undo restores access; cancelled
              processing stays cancelled.
            </p>
            <Button onClick={restoreArchived} disabled={busy}>
              Undo archive
            </Button>
          </div>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {active && (
          <nav className="view-tabs" aria-label="Workspace sections">
            {(
              [
                ["ask", SearchIcon, "Ask"],
                ["sources", FileText, "Sources"],
                ["saved", BookOpenText, "Saved research"],
              ] as const
            ).map(([id, Icon, label]) => (
              <Button
                key={id}
                className={view === id ? "active" : ""}
                aria-current={view === id ? "page" : undefined}
                onClick={() => setView(id)}
              >
                <Icon size={16} />
                {label}
              </Button>
            ))}
          </nav>
        )}
        {active && view === "sources" && (
          <details className="diagnostics">
            <summary>Collection details</summary>
            <p>
              {active.visibility === "curated" ? "Curated" : "Private"}{" "}
              collection
            </p>
            <p>
              Snapshot:{" "}
              <code>
                {active.active_snapshot ??
                  "Add sources to create a searchable snapshot"}
              </code>
            </p>
            <p>
              Sparse, dense and hybrid retrieval remain available in Ask → More
              options.
            </p>
          </details>
        )}
        {active && view === "ask" && !active.active_snapshot && (
          <section className="empty">
            <h2>Add your first sources</h2>
            <p>
              Your collection is ready for documents. Processing makes them
              searchable.
            </p>
            <Button variant="primary" onClick={() => setView("sources")}>
              Add documents
            </Button>
          </section>
        )}
        {active && view === "ask" && (
          <div className="ask-modes" role="group" aria-label="Question mode">
            <Button
              aria-pressed={askMode === "answer"}
              onClick={() => setAskMode("answer")}
            >
              Answer
            </Button>
            <Button
              aria-pressed={askMode === "passages"}
              onClick={() => setAskMode("passages")}
            >
              Find passages
            </Button>
          </div>
        )}
        {active && (
          <div hidden={view !== "sources"}>
            <Uploads
              key={active.collection_id}
              collection={active}
              session={session}
              refresh={refresh}
              fail={fail}
            />
          </div>
        )}
        {active && (
          <div hidden={view !== "ask" || askMode !== "passages"}>
            <Search
              key={`search-${active.collection_id}`}
              collection={active}
              session={session}
              fail={fail}
            />
          </div>
        )}
        {!active ? (
          <section className="empty">
            <span className="empty-symbol">
              <Sparkles size={30} />
            </span>
            <h2>Start with a collection</h2>
            <p>
              Create a collection for your research, then add your documents.
            </p>
            <Button
              variant="primary"
              onClick={() => {
                setNavigationOpen(true);
                requestAnimationFrame(() =>
                  document.getElementById("collection-title")?.focus(),
                );
              }}
            >
              Create collection
            </Button>
          </section>
        ) : null}
        {active && (
          <div
            hidden={
              view !== "saved" && (view !== "ask" || askMode !== "answer")
            }
          >
            <Research
              key={`research-${active.collection_id}`}
              showHistory={view === "saved"}
              collection={active}
              session={session}
              fail={fail}
            />
          </div>
        )}
        <footer>
          Paper evidence and RetrieVec measurements are distinct. Retrieval
          scores measure ranking, not scientific validity.
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
