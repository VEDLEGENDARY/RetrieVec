import { BookmarkCheck, BookmarkPlus, Copy, ExternalLink } from "lucide-react";
import { ActionLink, Button } from "../../ui";
import { highlightPassage } from "./lib/highlighting";
import { sourceHash } from "./lib/evidence";
import { MethodMark } from "./MethodMark";
import { methodNames, type Passage } from "./types";

export function PassageCard({
  passage,
  snapshot,
  query,
  shortlisted,
  selected,
  onShortlist,
  onInspect,
  onCopy,
}: {
  passage: Passage;
  snapshot: string;
  query: string;
  shortlisted: boolean;
  selected: boolean;
  onShortlist: () => void;
  onInspect: (trigger: HTMLButtonElement) => void;
  onCopy: () => void;
}) {
  const { hit, method, ranks } = passage;
  const metric = ranks[method]!;
  const hash = sourceHash(hit);
  const parts =
    method === "dense"
      ? [{ text: hit.text, highlighted: false }]
      : highlightPassage(hit.text, query);
  return (
    <article
      className="passage-card"
      data-passage={hit.chunk_id}
      data-method={method}
      data-selected={selected || undefined}
    >
      <header className="passage-card-heading">
        <div>
          <p className="passage-method">
            <MethodMark method={method} />
            {methodNames[method]}
          </p>
          <h3>
            <Button
              variant="quiet"
              className="passage-select"
              onClick={(event) => onInspect(event.currentTarget)}
            >
              {hit.title}
            </Button>
          </h3>
        </div>
        <dl className="passage-score">
          <div>
            <dt>Rank</dt>
            <dd className="metric">{metric.rank}</dd>
          </div>
          <div>
            <dt>{metric.label}</dt>
            <dd className="metric">
              {metric.score === null
                ? "Not reported"
                : metric.score.toFixed(method === "hybrid" ? 5 : 3)}
            </dd>
          </div>
        </dl>
      </header>
      <p className="provenance-line">
        <span title={hit.chunk_id}>Passage {hit.chunk_id}</span>
        <span title={snapshot}>Snapshot {snapshot}</span>
        <span title={hash ?? undefined}>
          Source SHA-256 {hash ? hash.slice(0, 12) : "unavailable"}
        </span>
      </p>
      <div
        className="passage-text"
        tabIndex={0}
        role="region"
        aria-label={`Passage text from ${hit.title}`}
      >
        <p>
          {parts.map((part, index) =>
            part.highlighted ? <mark key={index}>{part.text}</mark> : part.text,
          )}
        </p>
      </div>
      <footer className="passage-actions">
        <Button
          aria-label="Shortlist passage"
          aria-pressed={shortlisted}
          onClick={onShortlist}
        >
          {shortlisted ? (
            <BookmarkCheck aria-hidden="true" />
          ) : (
            <BookmarkPlus aria-hidden="true" />
          )}
          {shortlisted ? "Shortlisted" : "Shortlist"}
        </Button>
        {hit.source_id ? (
          <ActionLink
            href={`/api/v1/sources/${encodeURIComponent(hit.source_id)}?snapshot_id=${encodeURIComponent(snapshot)}#page=${hit.page_range?.[0] ?? 1}`}
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink aria-hidden="true" />
            Open source
          </ActionLink>
        ) : (
          <Button
            disabled
            title="Original file unavailable for this imported source"
          >
            <ExternalLink aria-hidden="true" />
            Open source unavailable
          </Button>
        )}
        <Button onClick={onCopy}>
          <Copy aria-hidden="true" />
          Copy citation
        </Button>
      </footer>
    </article>
  );
}

export function PassageSkeleton() {
  return (
    <article className="passage-card passage-skeleton" aria-hidden="true">
      <div className="skeleton short" />
      <div className="skeleton" />
      <div className="skeleton short" />
      <div className="skeleton" />
      <div className="skeleton" />
      <div className="skeleton" />
      <div className="skeleton short" />
    </article>
  );
}
