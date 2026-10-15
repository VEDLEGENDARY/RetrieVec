import type { Method } from "./types";
export type AtlasHighlight = {
  passageId: string;
  method: Method;
  rank: number;
};
export type AtlasPanelProps = {
  selectedPassageId: string | null;
  highlights: AtlasHighlight[];
};
export function AtlasPanel({ selectedPassageId, highlights }: AtlasPanelProps) {
  return (
    <div
      className="atlas-placeholder"
      data-selected-passage={selectedPassageId ?? undefined}
      data-highlight-count={highlights.length}
    >
      <p>Atlas arrives in task 04</p>
      <p className="muted">
        {selectedPassageId
          ? "The selected passage will be centered here."
          : "Select a passage to prepare its place in the Atlas."}
      </p>
    </div>
  );
}
