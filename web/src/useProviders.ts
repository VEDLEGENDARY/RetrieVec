import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Session } from "./api";
import type { Provider } from "./researchTypes";

/** One authorized provider list per active identity/collection. No consent writes. */
export function useProviders(
  collection: string | undefined,
  session: Session | null,
  fail: (error: unknown) => void,
) {
  const key = `${session?.principal_id ?? ""}:${collection ?? ""}`;
  const currentKey = useRef(key);
  currentKey.current = key;
  const request = useRef<AbortController | null>(null);
  const [state, setState] = useState<{
    key: string;
    rows: Provider[];
    selected: string;
    loaded: boolean;
  }>({ key: "", rows: [], selected: "", loaded: false });
  const refresh = useCallback(async () => {
    request.current?.abort();
    if (!collection || !session) return;
    const controller = new AbortController();
    request.current = controller;
    try {
      const rows = await api<Provider[]>(
        `/api/v1/collections/${collection}/providers`,
        { signal: controller.signal },
      );
      if (controller.signal.aborted || currentKey.current !== key) return;
      setState((previous) => ({
        key,
        rows,
        loaded: true,
        selected:
          previous.key === key &&
          rows.some((item) => item.name === previous.selected)
            ? previous.selected
            : (rows.find((item) => item.consented)?.name ??
              rows[0]?.name ??
              ""),
      }));
    } catch (error) {
      if (controller.signal.aborted || currentKey.current !== key) return;
      setState({ key, rows: [], selected: "", loaded: true });
      fail(error);
    }
  }, [collection, session?.principal_id, key, fail]);
  useEffect(() => {
    void refresh();
    return () => request.current?.abort();
  }, [refresh]);
  const active =
    state.key === key ? state : { rows: [], selected: "", loaded: false };
  const select = (selected: string) =>
    setState((previous) =>
      previous.key === key ? { ...previous, selected } : previous,
    );
  return {
    providers: active.rows,
    provider: active.selected,
    selectedProvider: active.rows.find((item) => item.name === active.selected),
    loaded: active.loaded,
    select,
    refresh,
  };
}
