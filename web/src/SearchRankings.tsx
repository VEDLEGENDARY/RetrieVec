import { Button } from "./ui";
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
  return (
    <div className={compact ? "rankings compact" : "rankings"}>
      {Object.entries(result.results)
        .filter(([name]) => method === "all" || name === method)
        .map(([mode, value]) => (
          <section key={mode} className="ranking" aria-label={labels[mode]}>
            <h3>{labels[mode]}</h3>
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
                      className={
                        selected?.chunk_id === hit.chunk_id
                          ? "hit active"
                          : "hit"
                      }
                      onClick={(event) => inspect(hit, event.currentTarget)}
                    >
                      <span className="hit-title">{hit.title}</span>
                      <span className="excerpt">{hit.text}</span>
                      <small>
                        {hit.page_range
                          ? `Page ${hit.page_range[0]}`
                          : "Page unavailable"}{" "}
                        ·{" "}
                        {value.reranker?.status === "applied" &&
                        hit.reranker_score !== undefined
                          ? `Reranker ${hit.reranker_score.toFixed(3)}`
                          : mode === "sparse"
                            ? `BM25 ${hit.bm25_score?.toFixed(3)}`
                            : mode === "dense"
                              ? `Cosine ${hit.cosine_score?.toFixed(3)}`
                              : `RRF ${hit.rrf_score?.toFixed(5)}`}
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
