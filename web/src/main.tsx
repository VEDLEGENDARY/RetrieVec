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
  Database,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  Search as SearchIcon,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type View = "overview" | "sources" | "search" | "answers";

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
  const [view, setView] = useState<View>("overview");
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
      setView("overview");
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
          <button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setNavigationOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <p className="eyebrow">Collections</p>
        <label className="collection-filter">
          Find a collection
          <input
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
                  setView("overview");
                  setNavigationOpen(false);
                }}
              >
                <span>{item.title}</span>
                <small>
                  {item.visibility === "curated" ? "Curated" : "Private"}
                </small>
              </button>
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
          <input
            id="collection-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={120}
            required
            placeholder="e.g. Retrieval methods"
          />
          <button disabled={busy || !title.trim()} type="submit">
            <Plus size={16} /> Create collection
          </button>
        </form>
        <div className="account">
          <span>
            <ShieldCheck size={14} /> Private workspace
          </span>
          <button onClick={logout}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </NavigationPanel>
      <main id="research" className="research">
        <div className="workspace-toolbar">
          <span>Library / {view === "answers" ? "Cited answers" : view}</span>
          <CommandMenu
            actions={[
              ...(active
                ? (["overview", "sources", "search", "answers"] as const)
                : []
              ).map((id) => ({
                id,
                label:
                  id === "answers"
                    ? "Cited answers"
                    : id.charAt(0).toUpperCase() + id.slice(1),
                detail: active?.title ?? "Workspace",
                run: () => setView(id),
              })),
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
                  setView("overview");
                  setError("");
                },
              })),
            ]}
          />
        </div>
        <header>
          <div>
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={navigationOpen}
              onClick={() => setNavigationOpen(true)}
            >
              <Menu size={19} />
            </button>
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
            <button className="quiet" onClick={archive} disabled={busy}>
              <Archive size={15} /> Archive collection
            </button>
          )}
        </header>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {active && (
          <nav className="view-tabs" aria-label="Workspace sections">
            {(
              [
                ["overview", LayoutDashboard, "Overview"],
                ["sources", FileText, "Sources"],
                ["search", SearchIcon, "Search"],
                ["answers", MessageSquareText, "Cited answers"],
              ] as const
            ).map(([id, Icon, label]) => (
              <button
                key={id}
                className={view === id ? "active" : ""}
                aria-current={view === id ? "page" : undefined}
                onClick={() => setView(id)}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </nav>
        )}
        {active && view === "overview" && (
          <section className="dashboard" aria-labelledby="overview-title">
            <div className="hero-card">
              <span className="hero-icon">
                <Sparkles size={24} />
              </span>
              <div>
                <p className="eyebrow">Collection overview</p>
                <h2 id="overview-title">
                  Turn papers into traceable evidence.
                </h2>
                <p>
                  Upload your source material, compare retrieval methods, and
                  build answers where every claim leads back to the original
                  passage.
                </p>
              </div>
              <button
                className="primary"
                onClick={() =>
                  setView(active.active_snapshot ? "search" : "sources")
                }
              >
                {active.active_snapshot
                  ? "Search this collection"
                  : "Add your first sources"}
                <ArrowUpRight size={16} />
              </button>
            </div>
            <div className="stat-grid">
              <article>
                <span>
                  <Database size={18} />
                </span>
                <small>Snapshot</small>
                <strong>
                  {active.active_snapshot ? "Active" : "Not created"}
                </strong>
                <p>
                  {active.active_snapshot
                    ? active.active_snapshot.slice(0, 16) + "…"
                    : "Upload sources to build one"}
                </p>
              </article>
              <article>
                <span>
                  <SearchIcon size={18} />
                </span>
                <small>Retrieval</small>
                <strong>3 modes</strong>
                <p>Sparse, dense and hybrid comparison</p>
              </article>
              <article>
                <span>
                  <ShieldCheck size={18} />
                </span>
                <small>Access</small>
                <strong>
                  {active.visibility === "curated" ? "Curated" : "Private"}
                </strong>
                <p>Identity-scoped sources and results</p>
              </article>
            </div>
            <div className="workflow-card">
              <div>
                <p className="eyebrow">Research flow</p>
                <h2>A clear path from document to answer</h2>
              </div>
              <ol>
                <li>
                  <span>01</span>
                  <div>
                    <strong>Add sources</strong>
                    <p>Import PDFs, Markdown, or text.</p>
                  </div>
                </li>
                <li>
                  <span>02</span>
                  <div>
                    <strong>Find evidence</strong>
                    <p>Compare exact retrieval methods.</p>
                  </div>
                </li>
                <li>
                  <span>03</span>
                  <div>
                    <strong>Build cited answers</strong>
                    <p>Save reproducible research runs.</p>
                  </div>
                </li>
              </ol>
            </div>
          </section>
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
          <div hidden={view !== "search"}>
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
              Give your research a home. Create a private collection, then add
              your source documents.
            </p>
          </section>
        ) : null}
        {active && (
          <div hidden={view !== "answers"}>
            <Research
              key={`research-${active.collection_id}`}
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
