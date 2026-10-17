import { Button } from "./ui";
import { useId, useLayoutEffect, useRef, useState } from "react";
import type { Evidence } from "./researchTypes";
export function Citation({
  item,
  number,
  snapshot,
  inspect,
  highlight,
}: {
  item: Evidence;
  number: number;
  snapshot: string;
  inspect: (item: Evidence, trigger: HTMLButtonElement) => void;
  highlight: (id: string | null) => void;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null),
    tooltip = useRef<HTMLSpanElement>(null);
  const [hovered, setHovered] = useState(false),
    [focused, setFocused] = useState(false),
    [dismissed, setDismissed] = useState(false);
  const [position, setPosition] = useState({ left: 16, top: 16 });
  const open = (hovered || focused) && !dismissed;
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect(),
        popup = tooltip.current?.getBoundingClientRect();
      if (!anchor || !popup) return;
      setPosition({
        left: Math.max(
          16,
          Math.min(anchor.left, innerWidth - popup.width - 16),
        ),
        top: Math.max(
          16,
          Math.min(anchor.bottom, innerHeight - popup.height - 16),
        ),
      });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);
  return (
    <span
      className="citation-preview-owner research-citation"
      onMouseEnter={() => {
        setHovered(true);
        setDismissed(false);
        highlight(item.evidence_id);
      }}
      onMouseLeave={() => {
        setHovered(false);
        if (!focused) highlight(null);
      }}
      onFocus={() => {
        setFocused(true);
        setDismissed(false);
        highlight(item.evidence_id);
      }}
      onBlur={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null))
          return;
        setFocused(false);
        if (!hovered) highlight(null);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          setDismissed(true);
          highlight(null);
        }
      }}
    >
      <Button
        ref={trigger}
        className="quiet citation"
        aria-label={`Inspect citation ${item.evidence_id}`}
        title={`Citation ${number}: ${item.title}`}
        aria-describedby={open ? id : undefined}
        onClick={(event) => {
          setDismissed(true);
          highlight(null);
          inspect(item, event.currentTarget);
        }}
      >
        [{number}]
      </Button>
      {open && (
        <span
          ref={tooltip}
          id={id}
          role="tooltip"
          className="citation-preview"
          style={position}
        >
          <strong>{item.title}</strong>
          <span className="citation-passage">{item.text}</span>
          <small>
            {item.page_range
              ? `Pages ${item.page_range.join("-")}`
              : "Page unavailable"}
          </small>
          <small>
            Snapshot <code>{item.snapshot_id ?? snapshot}</code>
          </small>
        </span>
      )}
    </span>
  );
}
