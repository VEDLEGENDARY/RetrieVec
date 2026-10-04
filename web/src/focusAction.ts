/** Reveal the native disclosures enclosing a command target, then restore useful focus. */
export function focusAction(id: string): boolean {
  const target = document.getElementById(id);
  if (!target) return false;
  for (
    let parent: HTMLElement | null = target;
    parent;
    parent = parent.parentElement
  ) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
  }
  if (target.closest("[hidden]") || target.matches(":disabled")) return false;
  const focus =
    target instanceof HTMLDetailsElement
      ? target.querySelector("summary")
      : target;
  focus?.focus();
  target.scrollIntoView({ block: "nearest" });
  return true;
}
