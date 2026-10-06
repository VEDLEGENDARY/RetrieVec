import { recordTiming } from "./performance";
import type { PaperMetadata } from "./PaperDetails";

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
export type Hit = PaperMetadata & {
  section?: string;
  section_heading?: string | null;
  text_offsets?: {
    unit: string;
    page: number | null;
    start: number;
    end: number;
  } | null;
  evidence_object_id?: string;
  evidence_type?: "prose" | "table" | "equation" | "figure";
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
    this.name = "APIError";
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  csrf?: string,
): Promise<T> {
  if (path !== "/api/v1/search") return request<T>(path, options, csrf);
  const started = performance.now();
  let outcome: "ok" | "error" = "error";
  try {
    const result = await request<T>(path, options, csrf);
    outcome = "ok";
    return result;
  } finally {
    recordTiming("retrieval.response", performance.now() - started, outcome);
  }
}

async function request<T>(
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
    const body: unknown = await response.json().catch(() => null);
    const error =
      body && typeof body === "object" ? (body as Record<string, unknown>) : {};
    const code =
      typeof error.code === "string" && /^[a-z_]{1,80}$/.test(error.code)
        ? error.code
        : "unavailable";
    const fallback =
      response.status === 401
        ? "Your session has ended. Sign in to continue."
        : response.status === 429
          ? "The workspace is busy. Wait a moment, then try again."
          : "The request could not be completed. Try again shortly.";
    const message =
      typeof error.message === "string" &&
      error.message.trim() &&
      error.message.length <= 1000
        ? error.message
        : fallback;
    throw new APIError(response.status, code, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
