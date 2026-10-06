import { Button } from "./ui";
import { useId, useState } from "react";
import type { Evidence } from "./researchTypes";
export function Citation({
  item,
  inspect,
}: {
  item: Evidence;
  inspect: (item: Evidence, trigger: HTMLButtonElement) => void;
}) {
  const id = useId();
  const [dismissed, setDismissed] = useState(false);
  return (
    <span
      className="citation-preview-owner"
      onMouseEnter={() => setDismissed(false)}
      onFocus={() => setDismissed(false)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          setDismissed(true);
        }
      }}
    >
      <Button
        className="quiet citation"
        aria-label={`Inspect citation ${item.evidence_id}`}
        aria-describedby={dismissed ? undefined : id}
        onClick={(event) => {
          setDismissed(true);
          inspect(item, event.currentTarget);
        }}
      >
        {item.title}
      </Button>
      {!dismissed && (
        <span id={id} role="tooltip" className="citation-preview">
          {item.text}
          <br />
          {item.page_range
            ? `Pages ${item.page_range.join("–")}`
            : "Page unavailable"}
        </span>
      )}
    </span>
  );
}
