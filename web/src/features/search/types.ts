import type { Hit, SearchResult } from "../../api";
import type { SavedPassage } from "../../EvidenceTray";

export const methods = ["sparse", "dense", "hybrid"] as const;
export type Method = (typeof methods)[number];
export const methodNames: Record<Method, string> = {
  sparse: "Sparse",
  dense: "Dense",
  hybrid: "Hybrid",
};
export const methodDetails: Record<Method, string> = {
  sparse: "BM25",
  dense: "Cosine",
  hybrid: "RRF",
};
export type SearchSpec = {
  query: string;
  snapshot: string;
  mode: string;
  section: string;
  rerank: boolean;
};
export type RecentSearch = SearchSpec & { method: Method; compare: boolean };
export type MethodRank = { rank: number; score: number | null; label: string };
export type ShortlistedPassage = SavedPassage & {
  ranks: Partial<Record<Method, MethodRank>>;
};
export type Passage = {
  hit: Hit;
  method: Method;
  methods: Method[];
  ranks: Partial<Record<Method, MethodRank>>;
};
export type SearchResponse = SearchResult;
