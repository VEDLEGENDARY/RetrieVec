import { useEffect, useId, useRef } from "react";
import { Download, X } from "lucide-react";
import { Button, IconButton, NativeDialog } from "../../ui";
import { MethodMark } from "./MethodMark";
import { passageIdentity, sourceHash } from "./lib/evidence";
import { methodNames, type Method, type ShortlistedPassage } from "./types";

export function CompareDrawer({
  open,
  items,
  onClose,
  onRemove,
  onExport,
}: {
  open: boolean;
  items: ShortlistedPassage[];
  onClose: () => void;
  onRemove: (key: string) => void;
  onExport: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null),
    returnTo = useRef<HTMLElement | null>(null);
  const title = useId();
  useEffect(() => {
    if (!open) {
      dialog.current?.close();
      return;
    }
    returnTo.current = document.activeElement as HTMLElement;
    dialog.current?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
      returnTo.current?.focus();
    };
  }, [open]);
  return (
    <NativeDialog
      ref={dialog}
      className="compare-drawer"
      aria-labelledby={title}
      onClose={onClose}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const targets = [
          ...event.currentTarget.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], [tabindex="0"]',
          ),
        ].filter((element) => element.getClientRects().length > 0);
        const first = targets[0],
          last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
    >
      <header className="compare-heading">
        <div>
          <h2 id={title}>Compare shortlisted passages</h2>
          <p>Up to six passages, each kept with its question and snapshot.</p>
        </div>
        <IconButton aria-label="Close comparison drawer" onClick={onClose}>
          <X aria-hidden="true" />
        </IconButton>
      </header>
      <div className="compare-toolbar">
        <p className="muted">
          Retrieval scores use different scales. Compare passages and sources,
          then judge the evidence.
        </p>
        <Button variant="primary" disabled={!items.length} onClick={onExport}>
          <Download aria-hidden="true" />
          Export shortlist
        </Button>
      </div>
      {!items.length ? (
        <p className="compare-empty">
          Your shortlist is empty. Use Shortlist on a passage to compare it
          here.
        </p>
      ) : (
        <div
          className="comparison-passages"
          tabIndex={0}
          role="region"
          aria-label="Side-by-side passage comparison"
        >
          {items.map((item) => (
            <article
              className="comparison-passage"
              key={passageIdentity(item.snapshot_id, item.hit.chunk_id)}
            >
              <div className="passage-heading">
                <h3>{item.hit.title}</h3>
                <IconButton
                  aria-label={`Remove ${item.hit.title} from shortlist`}
                  onClick={() =>
                    onRemove(
                      passageIdentity(item.snapshot_id, item.hit.chunk_id),
                    )
                  }
                >
                  <X aria-hidden="true" />
                </IconButton>
              </div>
              <dl className="comparison-ranks">
                {item.methods.map((method) => (
                  <div key={method}>
                    <dt>
                      <MethodMark method={method as Method} />
                      {methodNames[method as Method] ?? method}
                    </dt>
                    <dd className="metric">
                      Rank {item.ranks[method as Method]?.rank ?? "unavailable"}{" "}
                      · {item.ranks[method as Method]?.label ?? "Score"}{" "}
                      {item.ranks[method as Method]?.score?.toFixed(
                        method === "hybrid" ? 5 : 3,
                      ) ?? "unavailable"}
                    </dd>
                  </div>
                ))}
              </dl>
              <blockquote tabIndex={0}>{item.hit.text}</blockquote>
              <dl className="comparison-provenance">
                <dt>Question</dt>
                <dd>{item.query}</dd>
                <dt>Passage</dt>
                <dd>
                  <code>{item.hit.chunk_id}</code>
                </dd>
                <dt>Snapshot</dt>
                <dd>
                  <code>{item.snapshot_id}</code>
                </dd>
                <dt>Source SHA-256</dt>
                <dd>
                  <code>{sourceHash(item.hit) ?? "Unavailable"}</code>
                </dd>
                <dt>Authors / year</dt>
                <dd>
                  {item.hit.authors?.join(", ") || "Authors not reported"} ·{" "}
                  {item.hit.year ?? "Year not reported"}
                </dd>
                <dt>DOI</dt>
                <dd>{item.hit.doi ?? "Not reported"}</dd>
                <dt>Section</dt>
                <dd>
                  {item.hit.section_heading ??
                    item.hit.section ??
                    "Not reported"}
                </dd>
              </dl>
            </article>
          ))}
        </div>
      )}
    </NativeDialog>
  );
}
