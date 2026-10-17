export type Dataset = "scifact" | "scidocs";
export type Pipeline =
  | "default_sparse"
  | "default_dense"
  | "default_hybrid"
  | "tuned_sparse"
  | "tuned_hybrid";
export type BenchmarkRow = {
  dataset: Dataset;
  pipeline: Pipeline;
  ndcg10: number;
  recall100: number;
  mrr10: number;
  p50: number;
  p95: number;
  resultsSha256: string;
};
export type Benchmark = {
  date: string;
  source: string;
  sourceSha256: string;
  schemaSha256: string;
  rows: readonly BenchmarkRow[];
  corpora: readonly {
    dataset: Dataset;
    papers: number;
    queries: number;
    chunks: number;
    snapshot: string;
  }[];
  protocol: {
    documentRanking: string;
    latency: string;
    transfer: string;
    embedding: string;
    selection: string;
    candidateChunks: number;
    seed: number;
  };
};
