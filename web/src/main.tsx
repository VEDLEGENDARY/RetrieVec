import { focusAction } from "./focusAction";
import { useProviders } from "./useProviders";
import {
  Button,
  ActionLink,
  IconButton,
  Field,
  Input,
  Notice,
  LoadingState,
  Disclosure,
  EmptyState,
} from "./ui";
import { useEffect, useRef, useState } from "react";
import { recordTiming } from "./performance";
import { createRoot } from "react-dom/client";
import { api, type Collection } from "./api";
import "@fontsource-variable/newsreader/standard.css";
import "@fontsource-variable/newsreader/standard-italic.css";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "./style.css";
import "./research.css";
import { ThemeControl } from "./ThemeControl";
import { ResultsPage } from "./features/results/ResultsPage";
import { Welcome } from "./Welcome";
import { CollectionJourney, ResearchGuide } from "./ResearchGuide";
import { PaperLibrary } from "./PaperLibrary";
import { Uploads } from "./Uploads";
import { Search } from "./Search";
import { Research } from "./Research";
import { CommandMenu } from "./CommandMenu";
import { useWorkspace } from "./useWorkspace";
import { NavigationPanel } from "./NavigationPanel";
import { navigate, readRoute, useWorkspaceRoute } from "./routing";
import {
  BookOpenText,
  LogOut,
  Plus,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import {
  CollectionHeader,
  WorkspaceDestinations,
  destinationLabels as viewLabels,
  type Destination as View,
} from "./WorkspaceChrome";

function App() {
  const {
    session,
    loading,
    collections,
    selected,
    setSelected: setWorkspaceSelected,
    error,
    setError,
    refresh,
    fail,
    logout,
  } = useWorkspace();
  const currentPrincipal = useRef(session?.principal_id);
  currentPrincipal.current = session?.principal_id;
  const [title, setTitle] = useState("");
  useEffect(() => {
    if (!loading) recordTiming("app.ready", performance.now());
  }, [loading]);

  const [busy, setBusy] = useState(false);
  const [archived, setArchived] = useState<Collection | null>(null);
  useEffect(() => setArchived(null), [session?.principal_id]);
  const route = useWorkspaceRoute();
  const view = route.view;
  const setView = (view: View) =>
    navigate({ view, collection: readRoute().collection || selected });
  const setSelected = (collection: string) => {
    setWorkspaceSelected(collection);
    navigate({ collection, view: "ask", run: "" });
  };
  useEffect(() => {
    if (
      route.collection &&
      collections.some((item) => item.collection_id === route.collection)
    )
      setWorkspaceSelected(route.collection);
  }, [route.collection, collections, setWorkspaceSelected]);
  const [modeChoice, setModeChoice] = useState<{
    scope: string;
    mode: "passages" | "answer";
  } | null>(null);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [collectionFilter, setCollectionFilter] = useState("");
  const active = collections.find((item) => item.collection_id === selected);
  const generation = useProviders(active?.collection_id, session, fail);
  const scope =
    (session?.principal_id ?? "") + ":" + (active?.collection_id ?? "");
  const askMode =
    modeChoice?.scope === scope
      ? modeChoice.mode
      : route.run || generation.selectedProvider?.consented
        ? "answer"
        : "passages";
  const setAskMode = (mode: "passages" | "answer") =>
    setModeChoice({ scope, mode });
  useEffect(() => setModeChoice(null), [session?.principal_id]);
  const [commandNotice, setCommandNotice] = useState("");
  useEffect(() => setCommandNotice(""), [scope]);
  function reveal(
    view: View,
    mode: "answer" | "passages" | null,
    target: string,
    unavailable: string,
  ) {
    setView(view);
    if (mode) setAskMode(mode);
    setCommandNotice("");
    requestAnimationFrame(() => {
      if (!focusAction(target)) {
        setCommandNotice(unavailable);
        if (view === "saved") focusAction("saved-search");
      }
    });
  }
  const contextualCommands = active
    ? [
        ...[
          {
            id: "recent",
            label: "Restore a recent query",
            detail:
              "Recent searches in this collection; restores fields without submitting",
            target: "recent-searches",
            saved: false,
            unavailable: "Run a passage search to create a recent query.",
          },
          {
            id: "excerpts",
            label: "Compact or full excerpts",
            detail: "Change how returned passages are displayed",
            target: "excerpt-display",
            saved: false,
            unavailable:
              "Run a passage search before changing excerpt display.",
          },
          {
            id: "inspect",
            label: "Inspect passages and original sources",
            detail:
              "Retained passages, source preview, structured evidence and raw extraction",
            target: "search-based-on",
            saved: false,
            unavailable:
              "Run a passage search, then choose a passage to inspect its source.",
          },
          {
            id: "conversations",
            label: "Browse conversations",
            detail: "Select an existing conversation or start a new one",
            target: "conversation",
            saved: true,
            unavailable: "Select a collection to browse its conversations.",
          },
        ].map((action) => ({
          id: action.id,
          label: action.label,
          detail: action.detail,
          run: () =>
            reveal(
              action.saved ? "saved" : "ask",
              action.saved ? null : "passages",
              action.target,
              action.unavailable,
            ),
        })),
        {
          id: "upload",
          label: "Add sources — choose files",
          detail:
            "Focus the upload picker; owner access and idle processing required",
          run: () =>
            reveal(
              "sources",
              null,
              "documents",
              "The upload picker is unavailable. Check collection ownership and processing activity in Sources.",
            ),
        },
        {
          id: "composer",
          label: "Focus question composer",
          detail: "Ask in the current mode · Ctrl / Command + Enter to submit",
          run: () =>
            reveal(
              "ask",
              askMode,
              askMode === "answer" ? "research-question" : "question",
              "The composer is unavailable. Select a collection first.",
            ),
        },
        {
          id: "comparison",
          label: "Compare retrieval methods",
          detail:
            "Reveal comparison settings; activate Compare methods, then submit a question",
          run: () =>
            reveal(
              "ask",
              "passages",
              "compare-methods",
              "Select a searchable collection to compare retrieval methods.",
            ),
        },
        {
          id: "syntax",
          label: "Boolean syntax and retrieval method",
          detail:
            "More search options; selecting Boolean syntax uses sparse retrieval",
          run: () =>
            reveal(
              "ask",
              "passages",
              "parser",
              "Select a collection to configure passage search.",
            ),
        },
        {
          id: "filters",
          label: "Filter returned passages",
          detail: "Search first; filters apply only to existing results",
          run: () =>
            reveal(
              "ask",
              "passages",
              "passage-filter",
              "Run a passage search first, then filter the returned results.",
            ),
        },
        {
          id: "shortlist",
          label: "Evidence shortlist",
          detail:
            "Temporary selection; inspect, remove, or export shortlisted passages",
          run: () =>
            reveal(
              "ask",
              "passages",
              "passage-shortlist",
              "Select a collection to open its temporary shortlist.",
            ),
        },
        {
          id: "shortlist-export",
          label: "Export evidence shortlist",
          detail:
            "Requires at least one shortlisted passage; JSON preserves provenance",
          run: () =>
            reveal(
              "ask",
              "passages",
              "export-shortlist",
              "Shortlist a passage before exporting evidence.",
            ),
        },
        {
          id: "saved-lookup",
          label: "Find saved research",
          detail: "Search saved questions in this collection only",
          run: () =>
            reveal(
              "saved",
              null,
              "saved-search",
              "Select a collection to search its saved research.",
            ),
        },
        {
          id: "provider",
          label: "Answer provider and consent",
          detail:
            "Review model and local/cloud status; consent is always explicit",
          run: () =>
            reveal(
              "ask",
              "answer",
              "generation-provider",
              "Select a collection to review answer providers.",
            ),
        },
        {
          id: "follow-up",
          label: "Standalone follow-up query",
          detail: "More answer options; preserve the displayed question",
          run: () =>
            reveal(
              "ask",
              "answer",
              "effective-query",
              "Select a collection to edit a follow-up query.",
            ),
        },
        {
          id: "search-provenance",
          label: "Search snapshot and provenance",
          detail:
            "Requires search results; inspect the exact search configuration",
          run: () =>
            reveal(
              "ask",
              "passages",
              "search-diagnostics",
              "Run a passage search first to inspect its snapshot and configuration.",
            ),
        },
        {
          id: "run-provenance",
          label: "Saved run provenance",
          detail:
            "Choose a saved run first; snapshot, model revision, and effective query",
          run: () =>
            reveal(
              "saved",
              null,
              "run-provenance",
              "Choose a saved run to inspect its provenance.",
            ),
        },
        {
          id: "based-on",
          label: "Based on — used and retrieved evidence",
          detail:
            "Choose a saved answer first; distinguish citations from other retrieved candidates",
          run: () =>
            reveal(
              "saved",
              null,
              "answer-based-on",
              "Choose a completed saved answer to inspect its used and retrieved evidence.",
            ),
        },
        ...["Markdown", "BibTeX", "JSON", "CSV"].map((format) => ({
          id: "export-" + format,
          label: "Export saved answer as " + format,
          detail:
            "Choose a completed run first; review and activate the export control",
          run: () =>
            reveal(
              "saved",
              null,
              "run-export-" + format.toLowerCase(),
              "Choose a completed saved run before exporting its answer.",
            ),
        })),
        ...["pinned", "current"].map((snapshot) => ({
          id: "replay-" + snapshot,
          label: "Replay " + snapshot + " snapshot",
          detail:
            "Choose an inactive run first; review before starting paid or local generation",
          run: () =>
            reveal(
              "saved",
              null,
              "replay-" + snapshot,
              "Choose an inactive saved run before replaying it.",
            ),
        })),
      ]
    : [];
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
      if (currentPrincipal.current !== session?.principal_id) return;
      setSelected(result.collection_id);
      navigate({ collection: result.collection_id, view: "sources", run: "" });
      setNavigationOpen(false);
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
        <LoadingState label="Opening your workspace…" />
      </main>
    );
  if (!session) return <Welcome error={error} />;
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
            <BookOpenText size={18} aria-hidden="true" />
          </span>{" "}
          RetrieVec
          <IconButton
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setNavigationOpen(false)}
          >
            <X size={18} aria-hidden="true" />
          </IconButton>
        </div>
        <p className="sidebar-description">
          A library for every research question.
        </p>
        <p className="eyebrow">
          Collections{" "}
          <span className="collection-count">{collections.length}</span>
        </p>
        <Field className="collection-filter" label="Find a collection">
          <Input
            type="search"
            value={collectionFilter}
            onChange={(event) => setCollectionFilter(event.target.value)}
            placeholder="Filter collections…"
          />
        </Field>
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
          <Field label="New collection">
            <Input
              id="collection-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={120}
              required
              placeholder="e.g. My literature review"
            />
          </Field>
          <Button disabled={busy || !title.trim()} type="submit">
            <Plus size={16} aria-hidden="true" /> Create collection
          </Button>
        </form>
        <div className="account">
          <ThemeControl />
          <ResearchGuide />
          <ActionLink href="/results">Retrieval results</ActionLink>
          <span>
            <ShieldCheck size={14} aria-hidden="true" /> Private workspace
          </span>
          <Button onClick={logout}>
            <LogOut size={14} aria-hidden="true" /> Sign out
          </Button>
        </div>
      </NavigationPanel>
      <main id="research" className="research">
        <div className="workspace-toolbar">
          <span className="workspace-location">
            <BookOpenText size={16} aria-hidden="true" /> Paper workspace{" "}
            <span aria-hidden="true">/</span> {viewLabels[view]}
          </span>
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
              ...contextualCommands,
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
        {commandNotice && <Notice>{commandNotice}</Notice>}
        <CollectionHeader
          collection={active}
          busy={busy}
          navigationOpen={navigationOpen}
          onOpenNavigation={() => setNavigationOpen(true)}
          onArchive={archive}
        />
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
        {error && <Notice error>{error}</Notice>}
        {active && <WorkspaceDestinations selected={view} onSelect={setView} />}
        {active && !active.active_snapshot && (
          <CollectionJourney collection={active} onSelect={setView} />
        )}
        {active && view === "sources" && (
          <Disclosure className="diagnostics">
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
          </Disclosure>
        )}
        {active && view === "ask" && !active.active_snapshot && (
          <EmptyState
            title="Add your first sources"
            action={
              <Button variant="primary" onClick={() => setView("sources")}>
                Add documents
              </Button>
            }
          >
            Build your paper library with research PDFs or notes. Once
            processing finishes, ask questions across the collection and inspect
            the evidence.
          </EmptyState>
        )}
        {active && view === "ask" && (
          <div className="ask-mode-context">
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
            <p className="muted" role="status">
              {generation.selectedProvider
                ? `${generation.selectedProvider.model} · ${generation.selectedProvider.cloud ? "Cloud" : "Local"}${generation.selectedProvider.consented ? "" : " · Consent required. Find passages is available; open Answer to review consent."}`
                : generation.loaded
                  ? "No answer provider configured. Use Find passages to search; ask the workspace operator to configure cited answers."
                  : "Checking answer availability. Find passages is available for searchable collections."}
            </p>
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
              onSearch={() => setView("ask")}
            />
            {view === "sources" && (
              <PaperLibrary
                key={`papers-${active.collection_id}`}
                collection={active}
                fail={fail}
              />
            )}
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
          <EmptyState
            title="Start with a collection"
            icon={<Sparkles size={30} aria-hidden="true" />}
            action={
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
            }
          >
            Give your literature review a home. Create a collection for a topic
            or project, add your papers, and start finding evidence.
          </EmptyState>
        ) : null}
        {active && (
          <div
            hidden={
              view !== "saved" && (view !== "ask" || askMode !== "answer")
            }
          >
            <Research
              key={`research-${active.collection_id}`}
              providers={generation.providers}
              provider={generation.provider}
              setProvider={generation.select}
              refreshProviders={generation.refresh}
              showHistory={view === "saved"}
              linkedRun={
                route.collection === active.collection_id ? route.run : ""
              }
              collection={active}
              session={session}
              fail={fail}
            />
          </div>
        )}
        <footer>
          Verify the passage. Check the paper. Retrieval scores describe
          ranking, not scientific validity.
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  location.pathname.replace(/\/$/, "") === "/results" ? (
    <ResultsPage />
  ) : (
    <App />
  ),
);
