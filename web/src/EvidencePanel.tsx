import { Button, IconButton, Notice, Disclosure } from "./ui";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Copy, X } from "lucide-react";
/** Both passage search and cited answers use the same verification surface. */
export function EvidencePanel({
  title,
  text,
  pages,
  snapshot,
  onClose,
  children,
  highlighted = false,
}: {
  title: string;
  text: string;
  pages: number[] | null;
  snapshot: string;
  onClose: () => void;
  children?: ReactNode;
  highlighted?: boolean;
}) {
  const panel = useRef<HTMLElement>(null);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    panel.current?.focus();
    setNotice("");
  }, [title, text, snapshot]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        `${text}\n\nSource: ${title}\n${pages ? `Pages: ${pages.join("–")}` : "Page unavailable"}\nSnapshot: ${snapshot}\nRetained source passage; not a claim of scientific validity.`,
      );
      setNotice("Passage and citation copied.");
    } catch {
      setNotice("Copy failed. Select the passage text and copy it manually.");
    }
  }
  return (
    <aside
      ref={panel}
      tabIndex={-1}
      className={highlighted ? "inspector passage-highlighted" : "inspector"}
      aria-label="Evidence inspector"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          onClose();
        }
      }}
    >
      <div className="inspector-heading">
        <h3>Evidence</h3>
        <IconButton aria-label="Close evidence inspector" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </IconButton>
      </div>
      <h2>{title}</h2>
      <p className="muted">
        {pages ? `Pages ${pages.join("–")}` : "Page unavailable"}
      </p>
      <blockquote>{text}</blockquote>
      <Button onClick={copy}>
        <Copy size={20} aria-hidden="true" />
        Copy with citation
      </Button>
      {notice && <Notice>{notice}</Notice>}
      <Disclosure>
        <summary>Evidence provenance</summary>
        <p>
          Snapshot <code>{snapshot}</code>
        </p>
      </Disclosure>
      {children}
    </aside>
  );
}
