import { useEffect, useId, useRef, useState } from "react";
import { History } from "lucide-react";
import { Button } from "../../ui";
import { methodNames, type RecentSearch } from "./types";
export function RecentSearches({
  items,
  onSelect,
}: {
  items: RecentSearch[];
  onSelect: (item: RecentSearch) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null),
    trigger = useRef<HTMLButtonElement>(null),
    menu = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  return (
    <div
      className="recent-popover"
      ref={root}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null))
          setOpen(false);
      }}
    >
      <Button
        id="recent-searches"
        ref={trigger}
        type="button"
        disabled={!items.length}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <History aria-hidden="true" />
        Recent searches
      </Button>
      {open && (
        <div
          id={id}
          ref={menu}
          role="menu"
          aria-label="Recent searches"
          className="recent-menu"
          onKeyDown={(event) => {
            const choices = [
              ...event.currentTarget.querySelectorAll<HTMLElement>(
                '[role="menuitem"]',
              ),
            ];
            const current = choices.indexOf(
              document.activeElement as HTMLElement,
            );
            if (event.key === "Escape") {
              event.preventDefault();
              event.stopPropagation();
              setOpen(false);
              trigger.current?.focus();
            }
            if (
              ["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key) &&
              choices.length
            ) {
              event.preventDefault();
              const next =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? choices.length - 1
                    : (current +
                        (event.key === "ArrowDown" ? 1 : -1) +
                        choices.length) %
                      choices.length;
              choices[next]?.focus();
            }
          }}
        >
          {items.length ? (
            items.map((item, index) => (
              <Button
                key={`${item.query}-${index}`}
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onSelect(item);
                }}
              >
                <span>
                  {item.query}
                  <small>
                    {methodNames[item.method]} ·{" "}
                    {item.mode === "structured"
                      ? "Boolean / phrase"
                      : "Natural language"}
                  </small>
                </span>
              </Button>
            ))
          ) : (
            <p role="none">
              Your last five searches will appear here. Run a search to begin.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
