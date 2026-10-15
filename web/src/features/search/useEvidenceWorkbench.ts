import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  APIError,
  type Collection,
  type Hit,
  type SearchResult,
  type Session,
} from "../../api";
import { useDraft } from "../../drafts";
import {
  citationText,
  passageIdentity,
  passages,
  queryKey,
  shortlistExport,
  validateSearch,
} from "./lib/evidence";
import {
  methods,
  type Method,
  type Passage,
  type RecentSearch,
  type SearchSpec,
  type ShortlistedPassage,
} from "./types";

export function useEvidenceWorkbench(
  collection: Collection,
  session: Session,
  fail: (error: unknown) => void,
) {
  const [query, setQuery, draftSaved] = useDraft(
    session.principal_id,
    collection.collection_id,
    "question",
  );
  const [method, setMethod] = useState<Method>("hybrid");
  const [mode, setMode] = useState("free_text"),
    [section, setSection] = useState("");
  const [rerank, setRerank] = useState(false),
    [compare, setCompare] = useState(false);
  const [active, setActive] = useState<{
    spec: SearchSpec;
    result: SearchResult;
  } | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [filter, setFilter] = useState(""),
    [methodFilter, setMethodFilter] = useState("active");
  const [recent, setRecent] = useState<RecentSearch[]>([]),
    [shortlist, setShortlistState] = useState<ShortlistedPassage[]>([]);
  const shortlistRef = useRef<ShortlistedPassage[]>([]);
  function setShortlist(
    update:
      | ShortlistedPassage[]
      | ((items: ShortlistedPassage[]) => ShortlistedPassage[]),
  ) {
    const next =
      typeof update === "function" ? update(shortlistRef.current) : update;
    shortlistRef.current = next;
    setShortlistState(next);
  }
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<Hit | null>(null);
  const [removed, setRemoved] = useState<{
    item: ShortlistedPassage;
    index: number;
  } | null>(null);
  const cache = useRef(new Map<string, SearchResult>()),
    request = useRef<AbortController | null>(null);
  const attempted = useRef<{
    spec: SearchSpec;
    method: Method;
    compare: boolean;
    remember: boolean;
  } | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  async function load(
    spec: SearchSpec,
    requested: Method,
    all: boolean,
    remember: boolean,
    force = false,
  ) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    attempted.current = { spec, method: requested, compare: all, remember };
    setError("");
    setNotice("");
    setSelected(null);
    const key = queryKey(spec),
      saved = cache.current.get(key);
    function activate(result: SearchResult) {
      setActive({ spec: { ...spec, snapshot: result.snapshot_id }, result });
      const returned = passages(result, requested, "", "all");
      setShortlist((items) =>
        items.map((item) => {
          if (
            item.snapshot_id !== result.snapshot_id ||
            item.query !== spec.query
          )
            return item;
          const match = returned.find(
            (entry) => entry.hit.chunk_id === item.hit.chunk_id,
          );
          return match
            ? {
                ...item,
                methods: [...new Set([...item.methods, ...match.methods])],
                ranks: { ...item.ranks, ...match.ranks },
              }
            : item;
        }),
      );
      if (remember) {
        setFilter("");
        setMethodFilter("active");
        setRecent((current) =>
          [
            {
              ...spec,
              snapshot: result.snapshot_id,
              method: requested,
              compare: all,
            },
            ...current.filter(
              (item) =>
                !(
                  item.query === spec.query &&
                  item.method === requested &&
                  item.mode === spec.mode &&
                  item.section === spec.section &&
                  item.rerank === spec.rerank
                ),
            ),
          ].slice(0, 5),
        );
      }
    }
    if (
      !force &&
      saved?.results[requested] &&
      (!all || methods.every((name) => saved.results[name]))
    ) {
      activate(saved);
      setBusy(false);
      return;
    }
    setBusy(true);
    try {
      const response = validateSearch(
        await api<unknown>(
          "/api/v1/search",
          {
            method: "POST",
            signal: controller.signal,
            body: JSON.stringify({
              collection_id: collection.collection_id,
              snapshot_id: spec.snapshot,
              query: spec.query,
              mode: spec.mode,
              retrieval: all ? "compare" : requested,
              ...(spec.section ? { section: spec.section } : {}),
              rerank: spec.rerank && requested === "hybrid",
            }),
          },
          session.csrf_token,
        ),
        collection.collection_id,
      );
      if (controller.signal.aborted) return;
      if (response.snapshot_id !== spec.snapshot)
        throw new Error(
          "The server returned a different snapshot. Retained results are unchanged; retry the search.",
        );
      const pinnedKey = queryKey({ ...spec, snapshot: response.snapshot_id });
      const previous = cache.current.get(pinnedKey);
      const result = {
        ...response,
        results: { ...previous?.results, ...response.results },
      };
      cache.current.set(pinnedKey, result);
      if (cache.current.size > 12)
        cache.current.delete(cache.current.keys().next().value!);
      activate(result);
      const missing = (all ? methods : [requested]).filter(
        (name) => !result.results[name],
      );
      if (missing.length)
        setError(
          `${missing.map((name) => name[0].toUpperCase() + name.slice(1)).join(", ")} results were unavailable. Available methods are shown; retry to request the missing methods.`,
        );
    } catch (caught) {
      if (controller.signal.aborted) return;
      if (
        caught instanceof APIError &&
        [401, 403, 404].includes(caught.status)
      ) {
        cache.current.clear();
        setActive(null);
        setShortlist([]);
        setRecent([]);
        setRemoved(null);
        fail(caught);
      }
      setError(
        caught instanceof Error
          ? caught.message
          : "Search failed. Check the connection and retry.",
      );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function submit() {
    if (!query.trim() || !collection.active_snapshot) return;
    void load(
      {
        query: query.trim(),
        snapshot: collection.active_snapshot,
        mode,
        section,
        rerank,
      },
      method,
      compare && mode === "free_text",
      true,
    );
  }
  function selectMethod(next: Method) {
    setMethod(next);
    setSelected(null);
    setMethodFilter("active");
    setCompare(false);
    setRerank(false);
    if (busy && attempted.current) {
      const previous = attempted.current;
      void load(
        { ...previous.spec, rerank: false },
        next,
        false,
        previous.remember,
      );
    } else if (active)
      void load({ ...active.spec, rerank: false }, next, false, false);
    else if (attempted.current) {
      const previous = attempted.current;
      const spec = { ...previous.spec, rerank: false };
      attempted.current = { ...previous, spec, method: next, compare: false };
    }
  }
  const availableMethod = active?.result.results[method]
    ? method
    : (methods.find((name) => active?.result.results[name]) ?? method);
  const displayMethod = methods.includes(methodFilter as Method)
    ? (methodFilter as Method)
    : availableMethod;
  const visible = useMemo(
    () =>
      active
        ? passages(active.result, displayMethod, filter, methodFilter)
        : [],
    [active, displayMethod, filter, methodFilter],
  );
  function remove(key: string) {
    const shortlist = shortlistRef.current;
    const index = shortlist.findIndex(
      (item) => passageIdentity(item.snapshot_id, item.hit.chunk_id) === key,
    );
    if (index < 0) return;
    setRemoved({ item: shortlist[index], index });
    setShortlist((current) =>
      current.filter(
        (item) => passageIdentity(item.snapshot_id, item.hit.chunk_id) !== key,
      ),
    );
    setNotice("Passage removed from the shortlist.");
  }
  function toggle(passage: Passage) {
    const shortlist = shortlistRef.current;
    if (!active) return;
    const key = passageIdentity(
      active.result.snapshot_id,
      passage.hit.chunk_id,
    );
    if (
      shortlist.some(
        (item) => passageIdentity(item.snapshot_id, item.hit.chunk_id) === key,
      )
    )
      return remove(key);
    if (shortlist.length >= 6) {
      setNotice(
        "Your shortlist has six passages. Remove one before adding another.",
      );
      return;
    }
    setShortlist((current) => [
      ...current,
      {
        hit: passage.hit,
        snapshot_id: active.result.snapshot_id,
        query: active.spec.query,
        methods: passage.methods,
        ranks: passage.ranks,
      },
    ]);
    setNotice("Passage added to the evidence shortlist.");
  }
  function undo() {
    const shortlist = shortlistRef.current;
    if (
      !removed ||
      shortlist.length >= 6 ||
      shortlist.some(
        (item) =>
          passageIdentity(item.snapshot_id, item.hit.chunk_id) ===
          passageIdentity(removed.item.snapshot_id, removed.item.hit.chunk_id),
      )
    )
      return;
    setShortlist((current) => {
      const next = [...current];
      next.splice(Math.min(removed.index, next.length), 0, removed.item);
      return next;
    });
    setRemoved(null);
    setNotice("Passage restored to the shortlist.");
  }
  async function copy(hit: Hit, snapshot: string, question: string) {
    try {
      await navigator.clipboard.writeText(
        citationText(hit, snapshot, question),
      );
      setNotice("Passage and citation copied.");
    } catch {
      setNotice("Copy failed. Select the passage text and copy it manually.");
    }
  }
  function exportShortlist() {
    const url = URL.createObjectURL(
      new Blob(
        [
          JSON.stringify(
            shortlistExport(collection.collection_id, shortlistRef.current),
            null,
            2,
          ),
        ],
        { type: "application/json" },
      ),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "retrievec-evidence.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function restore(item: RecentSearch) {
    setQuery(item.query);
    setMethod(item.method);
    setMode(item.mode);
    setSection(item.section);
    setRerank(item.rerank);
    setCompare(item.compare);
  }
  return {
    query,
    setQuery,
    draftSaved,
    method,
    selectMethod,
    mode,
    setMode: (value: string) => {
      setMode(value);
      setRerank(false);
      setCompare(false);
      if (value === "structured") setMethod("sparse");
    },
    section,
    setSection,
    rerank,
    setRerank,
    compareMethods: () => {
      setMode("free_text");
      setCompare(true);
      setRerank(false);
    },
    compare,
    active,
    busy,
    error,
    filter,
    setFilter,
    methodFilter,
    setMethodFilter,
    recent,
    restore,
    shortlist,
    toggle,
    remove,
    removed,
    undo,
    notice,
    selected,
    setSelected,
    displayMethod,
    visible,
    submit,
    copy,
    exportShortlist,
    retry: () => {
      if (attempted.current) {
        const a = attempted.current;
        void load(a.spec, a.method, a.compare, a.remember, true);
      }
    },
    cancel: () => {
      request.current?.abort();
      setBusy(false);
      setNotice("Search cancelled. Previous results are still available.");
    },
  };
}
