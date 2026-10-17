import { Button } from "../../ui";
import type { Conversation, SavedRun } from "../../researchTypes";
export function ConversationRail({
  items,
  runs,
  selected,
  onSelect,
  onNew,
  loading,
  busy,
  error,
  onRetry,
}: {
  items: Conversation[];
  runs: SavedRun[];
  selected: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  loading: boolean;
  busy: boolean;
  error: string;
  onRetry: () => void;
}) {
  return (
    <aside className="conversation-rail" aria-label="Conversation rail">
      <h3>Conversations</h3>
      <Button disabled={busy} onClick={onNew}>
        Start a conversation
      </Button>
      {error ? (
        <div role="status">
          <p>{error}</p>
          <Button onClick={onRetry}>Reload conversations</Button>
        </div>
      ) : loading && !items.length ? (
        <p role="status">Loading conversations...</p>
      ) : (
        <nav aria-label="Research conversations">
          {items.map((item) => {
            const latest = runs.find(
              (run) => run.conversation_id === item.conversation_id,
            );
            const stamp = latest?.created_at || item.created_at;
            const date = stamp ? new Date(stamp) : null;
            const validDate = date && Number.isFinite(date.getTime());
            return (
              <Button
                key={item.conversation_id}
                disabled={busy}
                aria-pressed={selected === item.conversation_id}
                onClick={() => onSelect(item.conversation_id)}
              >
                <strong>{item.title}</strong>
                {validDate ? (
                  <time
                    dateTime={date.toISOString()}
                    title={latest ? "Latest saved run" : "Conversation created"}
                  >
                    {date.toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </time>
                ) : (
                  <small>Date unavailable</small>
                )}
                <span className="conversation-preview">
                  {latest?.original_question ??
                    item.preview ??
                    "Open to load the latest question"}
                </span>
              </Button>
            );
          })}
          {!items.length && !loading && (
            <p>Your saved conversations will appear here.</p>
          )}
        </nav>
      )}
    </aside>
  );
}
