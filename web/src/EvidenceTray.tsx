import { Button } from "./ui";
import { Download, BookmarkCheck, X } from "lucide-react";
import type { Hit } from "./api";

export type SavedPassage = {
  hit: Hit;
  snapshot_id: string;
  query: string;
  methods: string[];
};

export function passageKey(item: SavedPassage) {
  return `${item.snapshot_id}:${item.hit.chunk_id}`;
}

export function EvidenceTray({
  items,
  collectionId,
  remove,
}: {
  items: SavedPassage[];
  collectionId: string;
  remove: (key: string) => void;
}) {
  function download() {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            schema_version: 1,
            kind: "retrievec_evidence_shortlist",
            collection_id: collectionId,
            exported_at: new Date().toISOString(),
            passages: items,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "retrievec-evidence.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <details className="evidence-tray">
      <summary>
        <BookmarkCheck size={18} aria-hidden="true" /> Evidence shortlist{" "}
        <span className="count-pill">{items.length}/6</span>
      </summary>
      <div className="tray-body">
        <div className="tray-intro">
          <p>
            Compare up to six passages. Kept only in this collection’s current
            browser session; changing collections or reloading clears the
            shortlist.
          </p>
          <Button onClick={download} disabled={!items.length}>
            <Download size={16} aria-hidden="true" /> Export evidence
          </Button>
        </div>
        {items.length === 0 ? (
          <p className="no-results">
            Use “Shortlist passage” below any result to start comparing
            evidence.
          </p>
        ) : (
          <div className="passage-board">
            {items.map((item) => (
              <article key={passageKey(item)}>
                <div className="passage-heading">
                  <h3>{item.hit.title}</h3>
                  <Button
                    aria-label={`Remove ${item.hit.title} from shortlist`}
                    onClick={() => remove(passageKey(item))}
                  >
                    <X size={16} />
                  </Button>
                </div>
                <p className="passage-meta">
                  {item.hit.page_range
                    ? item.hit.page_range[0] === item.hit.page_range[1]
                      ? `Page ${item.hit.page_range[0]}`
                      : `Pages ${item.hit.page_range.join("–")}`
                    : "Page unavailable"}{" "}
                  · {item.methods.join(", ")}
                </p>
                <blockquote>{item.hit.text}</blockquote>
                <details>
                  <summary>Evidence provenance</summary>
                  <dl>
                    <dt>Question</dt>
                    <dd>{item.query}</dd>
                    <dt>Snapshot</dt>
                    <dd>{item.snapshot_id}</dd>
                    <dt>Passage</dt>
                    <dd>{item.hit.chunk_id}</dd>
                  </dl>
                </details>
              </article>
            ))}
          </div>
        )}
        <small>
          Exported passages retain their original snapshot and question.
          Retrieval scores are not evidence of scientific validity.
        </small>
      </div>
    </details>
  );
}
