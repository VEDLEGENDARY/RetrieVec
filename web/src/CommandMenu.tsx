import { useEffect, useRef, useState } from "react";
import { Command, Search, X } from "lucide-react";

export type CommandAction = {
  id: string;
  label: string;
  detail: string;
  run: () => void;
};

export function CommandMenu({ actions }: { actions: CommandAction[] }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const matches = actions.filter((action) =>
    `${action.label} ${action.detail}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  function open() {
    setQuery("");
    setSelected(0);
    dialog.current?.showModal();
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
      <button className="command-trigger" onClick={open}>
        <Command size={16} />
        Quick actions<kbd>Ctrl / ⌘ K</kbd>
      </button>
      <dialog
        ref={dialog}
        className="command-dialog"
        aria-labelledby="command-title"
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
      >
        <div className="command-body">
          <div className="command-heading">
            <h2 id="command-title">Find your next action</h2>
            <button
              aria-label="Close quick actions"
              onClick={() => dialog.current?.close()}
            >
              <X size={18} />
            </button>
          </div>
          <label className="command-input">
            <Search size={18} />
            <input
              autoFocus
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
                if (event.key === "Enter" && matches[selected]) {
                  event.preventDefault();
                  choose(matches[selected]);
                }
              }}
            />
          </label>
          <div className="command-results" aria-label="Matching actions">
            {matches.map((action, index) => (
              <button
                key={action.id}
                className={
                  selected === index
                    ? "command-result selected"
                    : "command-result"
                }
                onClick={() => choose(action)}
              >
                <span>
                  {action.label}
                  <small>{action.detail}</small>
                </span>
                <span aria-hidden="true">↵</span>
              </button>
            ))}
            {!matches.length && (
              <p role="status">
                No matching actions. Try a collection name or “search”.
              </p>
            )}
          </div>
          <p className="command-help">
            Use ↑ ↓ then Enter, or Tab to browse. Escape closes this menu.
          </p>
        </div>
      </dialog>
    </>
  );
}
