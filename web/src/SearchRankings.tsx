import { Button } from "./ui";
import { useEffect, useLayoutEffect, useRef } from "react";
import { BookmarkCheck, BookmarkPlus } from "lucide-react";
import type { Hit, SearchResult } from "./api";
import type { SavedPassage } from "./EvidenceTray";
export const labels: Record<string, string> = {
  sparse: "Sparse · BM25",
  dense: "Dense · Cosine",
  hybrid: "Hybrid · RRF",
};
export function SearchRankings({
  result,
  compact,
  method,
  filter,
  selected,
  shortlist,
  inspect,
  save,
}: {
  result: SearchResult;
  compact: boolean;
  method: string;
  filter: string;
  selected: Hit | null;
  shortlist: SavedPassage[];
  inspect: (hit: Hit, trigger: HTMLButtonElement) => void;
  save: (hit: Hit) => void;
}) {
  const rankings = useRef<HTMLDivElement>(null);
  const previous = useRef({
    method,
    positions: new Map<string, { left: number; top: number }>(),
  });
  const animations = useRef<Animation[]>([]);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const stop = () => {
      if (media.matches)
        animations.current.forEach((animation) => animation.cancel());
    };
    media.addEventListener("change", stop);
    return () => media.removeEventListener("change", stop);
  }, []);
  useLayoutEffect(() => {
    animations.current.forEach((animation) => animation.cancel());
    animations.current = [];
    const positions = new Map<string, { left: number; top: number }>();
    const changed = previous.current.method !== method;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const duration = parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue(
        "--motion-normal",
      ),
    );
    rankings.current
      ?.querySelectorAll<HTMLElement>("[data-passage]")
      .forEach((card) => {
        const key = card.dataset.passage!;
        const bounds = card.getBoundingClientRect();
        // Document coordinates keep scrolling out of the method-change motion.
        const rect = {
          left: bounds.left + window.scrollX,
          top: bounds.top + window.scrollY,
        };
        const before = previous.current.positions.get(key);
        if (changed && before && !reduced) {
          const x = before.left - rect.left,
            y = before.top - rect.top;
          if (x || y)
            animations.current.push(
              card.animate(
                [
                  { transform: `translate(${x}px, ${y}px)` },
                  { transform: "none" },
                ],
                { duration, easing: "ease-out" },
              ),
            );
        }
        if (!positions.has(key)) positions.set(key, rect);
      });
    previous.current = { method, positions };
  }, [method, result, filter, compact]);
  useLayoutEffect(
    () => () => animations.current.forEach((animation) => animation.cancel()),
    [],
  );
  return (
    <div ref={rankings} className={compact ? "rankings compact" : "rankings"}>
      {Object.entries(result.results)
        .filter(([name]) => method === "all" || name === method)
        .map(([mode, value]) => (
          <section
            key={mode}
            className="ranking"
            data-method={mode}
            aria-label={labels[mode] ?? mode}
          >
            <h3>
              <span className="retrieval-mark" aria-hidden="true" />
              {labels[mode] ?? mode}
            </h3>
            <small>
              {
                value.hits.filter((hit) =>
                  `${hit.title} ${hit.text}`
                    .toLowerCase()
                    .includes(filter.toLowerCase()),
                ).length
              }{" "}
              shown / {value.hits.length} returned · {value.total_matches}{" "}
              candidates
            </small>
            {!value.hits.some((hit) =>
              `${hit.title} ${hit.text}`
                .toLowerCase()
                .includes(filter.toLowerCase()),
            ) && (
              <p className="no-results">
                {filter
                  ? "No returned passages match this filter. Clear it or try another phrase."
                  : "No matching passages. Try a different question."}
              </p>
            )}
            <ol>
              {value.hits
                .filter((hit) =>
                  `${hit.title} ${hit.text}`
                    .toLowerCase()
                    .includes(filter.toLowerCase()),
                )
                .map((hit) => (
                  <li key={hit.chunk_id} value={hit.rank}>
                    <Button
                      data-passage={hit.chunk_id}
                      className={
                        selected?.chunk_id === hit.chunk_id
                          ? "hit active"
                          : "hit"
                      }
                      onClick={(event) => inspect(hit, event.currentTarget)}
                    >
                      <span className="hit-title">
                        <span className="retrieval-mark" aria-hidden="true" />
                        {hit.title}
                      </span>
                      <span className="excerpt">{hit.text}</span>
                      <small>
                        {hit.page_range
                          ? `Page ${hit.page_range[0]}`
                          : "Page unavailable"}{" "}
                        ·{" "}
                        <span className="metric">
                          {value.reranker?.status === "applied" &&
                          hit.reranker_score !== undefined
                            ? `Reranker ${hit.reranker_score.toFixed(3)}`
                            : mode === "sparse"
                              ? `BM25 ${hit.bm25_score?.toFixed(3)}`
                              : mode === "dense"
                                ? `Cosine ${hit.cosine_score?.toFixed(3)}`
                                : `RRF ${hit.rrf_score?.toFixed(5)}`}
                        </span>
                      </small>
                    </Button>
                    <Button
                      className="shortlist-action"
                      aria-pressed={shortlist.some(
                        (item) =>
                          item.snapshot_id === result.snapshot_id &&
                          item.hit.chunk_id === hit.chunk_id,
                      )}
                      onClick={() => save(hit)}
                    >
                      {shortlist.some(
                        (item) =>
                          item.snapshot_id === result.snapshot_id &&
                          item.hit.chunk_id === hit.chunk_id,
                      ) ? (
                        <BookmarkCheck size={15} aria-hidden="true" />
                      ) : (
                        <BookmarkPlus size={15} aria-hidden="true" />
                      )}{" "}
                      Shortlist passage
                    </Button>
                  </li>
                ))}
            </ol>
          </section>
        ))}
    </div>
  );
}
