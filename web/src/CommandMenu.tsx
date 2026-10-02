import { Button, Input } from "./ui";
import { useEffect, useId, useRef, useState } from "react";
import { Command, Search, X } from "lucide-react";

export type CommandAction = {
  id: string;
  label: string;
  detail: string;
  run: () => void;
};

export function CommandMenu({ actions }: { actions: CommandAction[] }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const matches = actions.filter((action) =>
    `${action.label} ${action.detail}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const activeIndex = Math.min(selected, matches.length - 1);
  const [opened, setOpened] = useState(false);
  useEffect(() => {
    if (opened && activeIndex >= 0) {
      document
        .getElementById(`${listId}-${activeIndex}`)
        ?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex, opened, listId, query]);
  function open() {
    setQuery("");
    setSelected(0);
    dialog.current?.showModal();
    setOpened(true);
    input.current?.focus();
  }
  function choose(action: CommandAction) {
    dialog.current?.close();
    action.run();
  }
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (dialog.current?.open) dialog.current.close();
        else open();
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  return (
    <>
      <Button className="command-trigger" onClick={open}>
        <Command size={16} />
        Quick actions<kbd>Ctrl / ⌘ K</kbd>
      </Button>
      <dialog
        ref={dialog}
        className="command-dialog"
        aria-labelledby="command-title"
        onClose={() => setOpened(false)}
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
      >
        <div className="command-body">
          <div className="command-heading">
            <h2 id="command-title">Find your next action</h2>
            <Button
              aria-label="Close quick actions"
              onClick={() => dialog.current?.close()}
            >
              <X size={18} />
            </Button>
          </div>
          <label className="command-input">
            <Search size={18} />
            <Input
              autoFocus
              ref={input}
              role="combobox"
              aria-expanded={opened}
              aria-autocomplete="list"
              aria-controls={listId}
              aria-activedescendant={
                activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined
              }
              aria-label="Find actions and collections"
              placeholder="Search actions or collections…"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setSelected(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  setSelected((index) =>
                    Math.max(
                      0,
                      Math.min(
                        matches.length - 1,
                        index + (event.key === "ArrowDown" ? 1 : -1),
                      ),
                    ),
                  );
                }
                if (event.key === "Home" || event.key === "End") {
                  event.preventDefault();
                  setSelected(
                    event.key === "Home" ? 0 : Math.max(0, matches.length - 1),
                  );
                }
                if (event.key === "Enter" && matches[activeIndex]) {
                  event.preventDefault();
                  choose(matches[activeIndex]);
                }
              }}
            />
          </label>
          <div
            id={listId}
            role="listbox"
            className="command-results"
            aria-label="Matching actions"
          >
            {matches.map((action, index) => (
              <Button
                key={action.id}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={activeIndex === index}
                tabIndex={-1}
                className={
                  activeIndex === index
                    ? "command-result selected"
                    : "command-result"
                }
                onClick={() => choose(action)}
                onMouseMove={() => setSelected(index)}
              >
                <span>
                  {action.label}
                  <small>{action.detail}</small>
                </span>
                <span aria-hidden="true">↵</span>
              </Button>
            ))}
          </div>
          {!matches.length && (
            <p role="status">
              No matching actions. Try a collection name or “search”.
            </p>
          )}
          <p className="command-help">
            Use ↑ ↓ to browse and Enter to choose. Escape closes this menu.
          </p>
        </div>
      </dialog>
    </>
  );
}
