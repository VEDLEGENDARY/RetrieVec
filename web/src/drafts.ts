import { useSyncExternalStore } from "react";

const prefix = "retrievec:draft:v1:";
const lifetime = 7 * 24 * 60 * 60 * 1000;
const changed = "retrievec:draft-change";
const memory = new Map<string, { text: string; expires: number }>();
const failures = new Set<string>();
const listeners = (notify: () => void) => {
  window.addEventListener(changed, notify);
  window.addEventListener("storage", notify);
  return () => {
    window.removeEventListener(changed, notify);
    window.removeEventListener("storage", notify);
  };
};
function read(key: string): string {
  const fallback = () => {
    const value = memory.get(key);
    if (value && value.expires > Date.now()) return value.text;
    memory.delete(key);
    return "";
  };
  if (failures.has(key) && memory.has(key)) return fallback();
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const value = JSON.parse(raw);
      if (
        typeof value.text === "string" &&
        value.text.length <= 4096 &&
        Number.isFinite(value.expires) &&
        value.expires > Date.now()
      )
        return value.text;
      localStorage.removeItem(key);
    }
    memory.delete(key);
    return "";
  } catch {
    failures.add(key);
  }
  return fallback();
}
export function clearDrafts(principal: string) {
  const scope = prefix + encodeURIComponent(principal) + ":";
  for (const key of memory.keys())
    if (key.startsWith(scope)) memory.delete(key);
  for (const key of failures) if (key.startsWith(scope)) failures.delete(key);
  try {
    for (const key of Object.keys(localStorage))
      if (key.startsWith(scope)) localStorage.removeItem(key);
  } catch {
    /* Storage may be disabled. */
  }
  window.dispatchEvent(new Event(changed));
}
/** A new authenticated principal must not inherit another account's device drafts. */
export function retainPrincipalDrafts(principal: string) {
  const scope = prefix + encodeURIComponent(principal) + ":";
  for (const key of memory.keys())
    if (!key.startsWith(scope)) memory.delete(key);
  for (const key of failures) if (!key.startsWith(scope)) failures.delete(key);
  try {
    for (const key of Object.keys(localStorage))
      if (key.startsWith(prefix) && !key.startsWith(scope))
        localStorage.removeItem(key);
  } catch {
    /* Memory-only drafts still remain scoped. */
  }
  window.dispatchEvent(new Event(changed));
}
/** Draft text only; protected answers and source passages never enter browser storage. */
export function useDraft(
  principal: string,
  collection: string,
  field: "question" | "follow-up",
) {
  const key = `${prefix}${encodeURIComponent(principal)}:${encodeURIComponent(collection)}:${field}`;
  const text = useSyncExternalStore(listeners, () => read(key));
  function update(value: string) {
    const text = value.slice(0, 4096);
    const expires = Date.now() + lifetime;
    memory.set(key, { text, expires });
    if (memory.size > 100) memory.delete(memory.keys().next().value!);
    try {
      if (text) localStorage.setItem(key, JSON.stringify({ text, expires }));
      else localStorage.removeItem(key);
      failures.delete(key);
    } catch {
      failures.add(key);
    }
    window.dispatchEvent(new Event(changed));
  }
  return [text, update, !failures.has(key)] as const;
}
