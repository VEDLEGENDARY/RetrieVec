export type Conversation = { conversation_id: string; title: string };
export type SavedRun = {
  run_id: string;
  conversation_id: string;
  original_question: string;
  state: string;
  created_at: string;
};
export type Provider = {
  name: string;
  model: string;
  cloud: boolean;
  consented: boolean;
};
export type Evidence = {
  chunk_id?: string;
  evidence_object_id?: string;
  evidence_id: string;
  citation_id: string;
  title: string;
  text: string;
  page_range: number[] | null;
  source_id: string | null;
  snapshot_id?: string;
};
export type Claim = { id: string; text: string; evidence_ids: string[] };
export type Comparison = {
  method: string;
  dataset: string;
  metric: string;
  reported_value: string;
  experimental_conditions: string;
  limitations: string;
  evidence_ids: string[];
  comparability_note: string;
};
export type Run = {
  run_id: string;
  conversation_id: string;
  original_question: string;
  effective_query: string;
  snapshot_id: string;
  state: string;
  error_code: string | null;
  configuration: {
    section?: string | null;
    provider: string;
    retrieval: string;
    generation: { model: string; revision: string };
  };
  result: null | {
    answer: {
      status: string;
      claims: Claim[];
      comparisons: Comparison[];
      limitations: string[];
    };
    evidence: Evidence[];
    elapsed_ms: number;
    budget: { excluded: unknown[]; input_tokens: number };
  };
};
