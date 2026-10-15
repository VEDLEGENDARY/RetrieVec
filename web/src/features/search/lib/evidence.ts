import type { Hit, SearchResult } from "../../../api";
import {
  methods,
  methodDetails,
  type Method,
  type Passage,
  type SearchSpec,
  type ShortlistedPassage,
} from "../types.ts";

export function queryKey(spec: SearchSpec) {
  return JSON.stringify([
    spec.snapshot,
    spec.query.trim(),
    spec.mode,
    spec.section,
    spec.rerank,
  ]);
}
export function passageIdentity(snapshot: string, id: string) {
  return `${snapshot}:${id}`;
}
export function sourceHash(hit: Hit): string | null {
  const hash = hit.source_sha256 ?? hit.source_hash;
  return typeof hash === "string" && /^[a-f\d]{64}$/i.test(hash) ? hash : null;
}
export function score(hit: Hit, method: Method, reranked = false) {
  const value = reranked
    ? hit.reranker_score
    : method === "sparse"
      ? hit.bm25_score
      : method === "dense"
        ? hit.cosine_score
        : hit.rrf_score;
  return {
    rank: hit.rank,
    score: typeof value === "number" && Number.isFinite(value) ? value : null,
    label: reranked ? "Reranker" : methodDetails[method],
  };
}
export function passages(
  result: SearchResult,
  method: Method,
  filter: string,
  methodFilter: string,
): Passage[] {
  const order = methods.includes(methodFilter as Method)
    ? (methodFilter as Method)
    : method;
  const entries = new Map<string, Passage>();
  for (const name of methods)
    for (const hit of result.results[name]?.hits ?? []) {
      const rank = score(
        hit,
        name,
        result.results[name].reranker?.status === "applied",
      );
      const current = entries.get(hit.chunk_id) ?? {
        hit,
        method: name,
        methods: [],
        ranks: {},
      };
      current.methods.push(name);
      current.ranks[name] = rank;
      if (name === order) {
        current.hit = hit;
        current.method = name;
      }
      entries.set(hit.chunk_id, current);
    }
  const shownMethod = methodFilter === "active" ? method : methodFilter;
  const needle = filter.trim().toLocaleLowerCase();
  return [...entries.values()]
    .filter(
      (entry) =>
        (shownMethod === "all" ||
          entry.methods.includes(shownMethod as Method)) &&
        `${entry.hit.title} ${entry.hit.text}`
          .toLocaleLowerCase()
          .includes(needle),
    )
    .sort(
      (a, b) =>
        (a.ranks[order]?.rank ?? Infinity) -
          (b.ranks[order]?.rank ?? Infinity) ||
        a.hit.chunk_id.localeCompare(b.hit.chunk_id),
    );
}
export function shortlistExport(
  collectionId: string,
  items: ShortlistedPassage[],
  exportedAt = new Date().toISOString(),
) {
  if (items.length > 6)
    throw new Error("A shortlist can contain at most six passages.");
  return {
    schema_version: 1,
    kind: "retrievec_evidence_shortlist",
    collection_id: collectionId,
    exported_at: exportedAt,
    passages: items.map((item) => ({
      ...item,
      methods: [...item.methods],
      ranks: { ...item.ranks },
      hit: { ...item.hit },
    })),
  };
}
export function citationText(hit: Hit, snapshot: string, query: string) {
  return `${hit.text}\n\nSource: ${hit.title}\n${hit.page_range ? `Pages: ${hit.page_range.join("–")}` : "Page unavailable"}\nPassage: ${hit.chunk_id}\nSnapshot: ${snapshot}\nSource SHA-256: ${sourceHash(hit) ?? "unavailable"}\nQuestion: ${query}`;
}
export function validateSearch(
  value: unknown,
  collectionId: string,
): SearchResult {
  const candidate = value as SearchResult | null;
  if (
    !candidate ||
    typeof candidate.snapshot_id !== "string" ||
    !candidate.snapshot_id ||
    typeof candidate.query !== "string" ||
    (candidate.collection_id && candidate.collection_id !== collectionId) ||
    !candidate.results ||
    typeof candidate.results !== "object"
  )
    throw new Error("The search response was incomplete. Retry the search.");
  for (const method of methods) {
    const ranking = candidate.results[method];
    if (!ranking) continue;
    if (
      !Array.isArray(ranking.hits) ||
      ranking.hits.some(
        (hit) =>
          typeof hit.chunk_id !== "string" ||
          typeof hit.title !== "string" ||
          typeof hit.text !== "string" ||
          !Number.isFinite(hit.rank),
      )
    )
      throw new Error("Returned passages were incomplete. Retry the search.");
  }
  if (!methods.some((method) => candidate.results[method]))
    throw new Error(
      "No retrieval method returned a usable response. Retry the search.",
    );
  return candidate;
}
