export type Session = { principal_id: string; csrf_token: string };
export type Job = {
  job_id: string;
  collection_id: string;
  state: string;
  stage: string;
  progress: Record<string, unknown>;
  error_code: string | null;
  output_snapshot: string | null;
};
export type Hit = {
  rank: number;
  chunk_id: string;
  title: string;
  text: string;
  source_id: string | null;
  page_range: [number, number] | null;
  bm25_score: number | null;
  cosine_score: number | null;
  rrf_score: number | null;
};
export type SearchResult = {
  snapshot_id: string;
  collection_id: string;
  query: string;
  mode: string;
  results: Record<
    string,
    {
      hits: Hit[];
      total_matches: number;
      configuration: Record<string, unknown>;
    }
  >;
};
export type Collection = {
  collection_id: string;
  title: string;
  visibility: "private" | "curated";
  active_snapshot: string | null;
  can_manage: boolean;
};
export class APIError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  csrf?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (csrf) headers.set("X-CSRF-Token", csrf);
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({
        code: "unavailable",
        message: "Service unavailable. Try again.",
      }));
    throw new APIError(response.status, error.code, error.message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
