import { useCallback, useEffect, useRef, useState } from "react";
import { api, APIError, type Collection, type Session } from "./api";
import { clearDrafts, retainPrincipalDrafts } from "./drafts";
import { navigate, readRoute } from "./routing";

/** Own session lifetime here so late refreshes cannot restore signed-out data. */
export function useWorkspace() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const epoch = useRef(0);
  const principal = useRef<string | null>(null);
  const latestRefresh = useRef(0);
  const activeRequests = useRef(new Set<AbortController>());

  const clearSession = useCallback(() => {
    if (principal.current) clearDrafts(principal.current);
    principal.current = null;
    epoch.current += 1;
    activeRequests.current.forEach((request) => request.abort());
    activeRequests.current.clear();
    setSession(null);
    setCollections([]);
    setSelected("");
    navigate({ collection: "", run: "", view: "ask" }, true);
  }, []);

  const fail = useCallback(
    (cause: unknown) => {
      if (cause instanceof Error && cause.name === "AbortError") return;
      if (cause instanceof APIError && cause.status === 401) clearSession();
      if (cause instanceof APIError && cause.status === 404) {
        setSelected("");
        setCollections([]);
      }
      setError(
        cause instanceof Error ? cause.message : "Request failed. Try again.",
      );
    },
    [clearSession],
  );

  const refresh = useCallback(async () => {
    const controller = new AbortController();
    activeRequests.current.add(controller);
    const generation = epoch.current;
    const request = ++latestRefresh.current;
    try {
      const values = await api<Collection[]>("/api/v1/collections", {
        signal: controller.signal,
      });
      if (generation !== epoch.current || request !== latestRefresh.current)
        return;
      setCollections(values);
      setSelected((current) =>
        values.some((item) => item.collection_id === current)
          ? current
          : (values.find(
              (item) => item.collection_id === readRoute().collection,
            )?.collection_id ??
            values[0]?.collection_id ??
            ""),
      );
    } finally {
      activeRequests.current.delete(controller);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const generation = epoch.current;
    api<Session>("/api/v1/me", { signal: controller.signal })
      .then(async (value) => {
        if (controller.signal.aborted || generation !== epoch.current) return;
        principal.current = value.principal_id;
        retainPrincipalDrafts(value.principal_id);
        setSession(value);
        await refresh();
      })
      .catch((cause) => {
        if (
          !controller.signal.aborted &&
          !(cause instanceof APIError && cause.status === 401)
        )
          fail(cause);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      epoch.current += 1;
      activeRequests.current.forEach((request) => request.abort());
      activeRequests.current.clear();
    };
  }, [refresh, fail]);

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" }, session?.csrf_token);
      clearSession();
      setError("");
    } catch (cause) {
      fail(cause);
    }
  }

  return {
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
  };
}
