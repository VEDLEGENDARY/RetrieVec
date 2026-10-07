import { useState } from "react";
import { Disclosure, Notice } from "./ui";

export type LocationMetadata = {
  pdf_locator?: {
    page: number;
    width: number;
    height: number;
    boxes: [number, number, number, number][];
    coordinates: string;
    extractor: string;
  } | null;
  locator_limitation?: string | null;
};

export function PassageLocation({
  passage,
  collectionId,
  snapshotId,
  chunkId,
}: {
  passage: LocationMetadata;
  collectionId: string;
  snapshotId: string;
  chunkId: string;
}) {
  const [unavailable, setUnavailable] = useState(false);
  const locator = passage.pdf_locator;
  if (!locator)
    return (
      <p>
        {passage.locator_limitation ??
          "No verified PDF location retained. Read the passage text; its original position cannot be highlighted."}
      </p>
    );
  const path = `/api/v1/collections/${encodeURIComponent(collectionId)}/snapshots/${encodeURIComponent(snapshotId)}/evidence/${encodeURIComponent(chunkId)}/pdf-page`;
  return (
    <Disclosure>
      <summary>Passage on original page {locator.page}</summary>
      {unavailable ? (
        <Notice>
          The retained page image is unavailable. Read the passage text or open
          the original source.
        </Notice>
      ) : (
        <div className="pdf-passage-location">
          <img
            src={path}
            alt={`Original page ${locator.page}`}
            onError={() => setUnavailable(true)}
          />
          <svg
            viewBox={`0 0 ${locator.width} ${locator.height}`}
            role="img"
            aria-label="Verified passage highlight"
          >
            {locator.boxes.map(([x0, y0, x1, y1], index) => (
              <rect
                key={index}
                x={x0}
                y={y0}
                width={x1 - x0}
                height={y1 - y0}
              />
            ))}
          </svg>
        </div>
      )}
      <p>
        Highlight follows retained PDF glyph coordinates; extraction is not a
        semantic support judgment.
      </p>
    </Disclosure>
  );
}
