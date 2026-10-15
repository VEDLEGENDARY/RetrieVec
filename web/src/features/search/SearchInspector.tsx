import { useState } from "react";
import type { Hit } from "../../api";
import { ActionLink } from "../../ui";
import { EvidencePanel } from "../../EvidencePanel";
import { PaperDetails } from "../../PaperDetails";
import { PassageLocation } from "../../PassageLocation";
import { AdvancedEvidence } from "../../AdvancedEvidence";
export function SearchInspector({
  hit,
  snapshot,
  collectionId,
  onClose,
}: {
  hit: Hit;
  snapshot: string;
  collectionId: string;
  onClose: () => void;
}) {
  const [error, setError] = useState("");
  const url = hit.source_id
    ? `/api/v1/sources/${encodeURIComponent(hit.source_id)}?snapshot_id=${encodeURIComponent(snapshot)}#page=${hit.page_range?.[0] ?? 1}`
    : null;
  return (
    <EvidencePanel
      title={hit.title}
      text={hit.text}
      pages={hit.page_range}
      snapshot={snapshot}
      onClose={onClose}
    >
      <PaperDetails paper={hit} />
      {hit.evidence_object_id ? (
        <AdvancedEvidence
          collectionId={collectionId}
          snapshotId={snapshot}
          chunkId={hit.chunk_id}
        />
      ) : (
        <PassageLocation
          passage={hit}
          collectionId={collectionId}
          snapshotId={snapshot}
          chunkId={hit.chunk_id}
        />
      )}
      {url && !hit.evidence_object_id ? (
        <>
          <ActionLink
            className="source-link"
            target="_blank"
            rel="noreferrer"
            href={url}
          >
            Open original source
          </ActionLink>
          <iframe
            title="Original source preview"
            src={url}
            onError={() =>
              setError(
                "Preview unavailable. Open the original source in a new tab.",
              )
            }
          />
          {error && <p role="status">{error}</p>}
          <p className="muted">
            The passage is shown separately; exact PDF highlights require
            verified retained coordinates.
          </p>
        </>
      ) : (
        !hit.evidence_object_id && (
          <p>
            Original file unavailable for this imported source. The pinned
            extracted passage is shown above.
          </p>
        )
      )}
    </EvidencePanel>
  );
}
