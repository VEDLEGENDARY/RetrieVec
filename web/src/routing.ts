import { useSyncExternalStore } from "react";

export type WorkspaceRoute = {
  view: "ask" | "sources" | "saved";
  collection: string;
  run: string;
};
const changed = "retrievec:route";
function subscribe(notify: () => void) {
  window.addEventListener("popstate", notify);
  window.addEventListener("hashchange", notify);
  window.addEventListener(changed, notify);
  return () => {
    window.removeEventListener("popstate", notify);
    window.removeEventListener("hashchange", notify);
    window.removeEventListener(changed, notify);
  };
}
export function readRoute(): WorkspaceRoute {
  const params = new URLSearchParams(location.hash.slice(1));
  const view = params.get("view");
  const identity = (key: string) => {
    const value = params.get(key) ?? "";
    return /^[\w-]{1,128}$/.test(value) ? value : "";
  };
  return {
    view: view === "sources" || view === "saved" ? view : "ask",
    collection: identity("collection"),
    run: identity("run"),
  };
}
export function navigate(patch: Partial<WorkspaceRoute>, replace = false) {
  const route = { ...readRoute(), ...patch };
  const params = new URLSearchParams({ view: route.view });
  if (route.collection) params.set("collection", route.collection);
  if (route.run) params.set("run", route.run);
  const hash = `#${params}`;
  if (hash === location.hash) return;
  history[replace ? "replaceState" : "pushState"](null, "", hash);
  window.dispatchEvent(new Event(changed));
}
export function useWorkspaceRoute() {
  useSyncExternalStore(subscribe, () => location.hash);
  return readRoute();
}
