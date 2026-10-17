import { readFile, writeFile, mkdir, copyFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { gunzipSync, gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { format } from "prettier";

const web = new URL("../", import.meta.url);
const reportName = "benchmark-2026-10-01.json";
export const expectedSchema =
  "94d245ef472cbb8397e7a1aa3514c4359fb5cc4110eec214955300d862d5c805";
const pipelines = [
  "default_sparse",
  "default_dense",
  "default_hybrid",
  "tuned_sparse",
  "tuned_hybrid",
];
export const sha256 = (value) =>
  createHash("sha256").update(value).digest("hex");

// Fingerprint structure, including array element unions, without copying query data to the client.
export function schemaShape(value) {
  if (value === null) return "null";
  if (Array.isArray(value))
    return [
      "array",
      [...new Set(value.map((item) => JSON.stringify(schemaShape(item))))]
        .sort()
        .map((item) => JSON.parse(item)),
    ];
  if (typeof value === "object")
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, schemaShape(value[key])]),
    );
  return typeof value;
}
export const schemaHash = (value) => sha256(JSON.stringify(schemaShape(value)));
function assert(condition, message) {
  if (!condition) throw new Error(`Benchmark schema: ${message}`);
}
export function projectBenchmark(value, rawHash) {
  assert(
    schemaHash(value) === expectedSchema,
    "structure changed; review the report schema before updating the sync script",
  );
  assert(
    value.schema_version === 1 &&
      value.kind === "full-beir" &&
      value.complete === true &&
      value.quality_evidence === true,
    "requires a complete full BEIR report",
  );
  assert(
    value.protocol.candidate_chunks === 100 &&
      JSON.stringify(value.protocol.metrics) ===
        JSON.stringify(["ndcg@10", "recall@100", "mrr@10"]),
    "metric cutoffs or candidate pool changed",
  );
  const rows = [],
    corpora = [];
  for (const dataset of ["scifact", "scidocs"]) {
    const source = value.datasets[dataset];
    assert(
      source.prepared.subset === false && source.prepared.document_limit === 0,
      `${dataset} is a subset`,
    );
    corpora.push({
      dataset,
      papers: source.prepared.papers,
      queries: source.query_count,
      chunks: source.prepared.chunks,
      snapshot: source.prepared.snapshot_id,
    });
    for (const pipeline of pipelines) {
      const run = source.runs[pipeline];
      assert(
        run.schema_version === 1 &&
          run.dataset_id === dataset &&
          run.cutoff === 10 &&
          run.split === "test" &&
          run.includes_drafts === false,
        `${dataset}/${pipeline} protocol mismatch`,
      );
      assert(
        run.failures.length === 0 &&
          run.missing_queries.length === 0 &&
          run.per_query.length === source.query_count,
        `${dataset}/${pipeline} has incomplete queries`,
      );
      for (const score of Object.values(run.metrics))
        assert(
          Number.isFinite(score) && score >= 0 && score <= 1,
          "quality metric outside [0,1]",
        );
      assert(
        Number.isFinite(run.latency_ms.p50) &&
          run.latency_ms.p50 >= 0 &&
          Number.isFinite(run.latency_ms.p95) &&
          run.latency_ms.p95 >= run.latency_ms.p50,
        "invalid latency percentiles",
      );
      assert(
        /^[a-f0-9]{64}$/.test(run.results_sha256),
        "missing results identity",
      );
      rows.push({
        dataset,
        pipeline,
        ndcg10: run.metrics.ndcg,
        recall100: run.metrics.recall,
        mrr10: run.metrics.mrr,
        p50: run.latency_ms.p50,
        p95: run.latency_ms.p95,
        resultsSha256: run.results_sha256,
      });
    }
  }
  return {
    date: "2026-10-01",
    source: reportName,
    sourceSha256: rawHash,
    schemaSha256: expectedSchema,
    rows,
    corpora,
    protocol: {
      documentRanking: value.protocol.document_ranking,
      latency: value.protocol.latency,
      transfer: value.protocol.scidocs_policy,
      embedding: value.protocol.embedding,
      selection: value.protocol.selection,
      candidateChunks: value.protocol.candidate_chunks,
      seed: value.protocol.seed,
    },
  };
}
export async function readSource() {
  for (const suffix of ["", ".gz"]) {
    const path = new URL(`../docs/results/${reportName}${suffix}`, web);
    try {
      const bytes = await readFile(path);
      return {
        bytes,
        raw: suffix ? gunzipSync(bytes) : bytes,
        path,
        compressed: !!suffix,
      };
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  // Isolated web/container builds use a byte-identical mirror of the single authoritative report.
  const path = new URL(`benchmarks/${reportName}.gz`, web);
  const bytes = await readFile(path);
  return { bytes, raw: gunzipSync(bytes), path, compressed: true };
}
export async function syncResults(check = false) {
  const source = await readSource();
  const data = projectBenchmark(JSON.parse(source.raw), sha256(source.raw));
  const output = await format(
    `// Generated by scripts/sync-results.mjs. Do not edit benchmark values here.\nimport type { Benchmark } from "./types";\nexport const benchmark = ${JSON.stringify(data, null, 2)} as const satisfies Benchmark;\n`,
    { parser: "typescript" },
  );
  const target = new URL("src/features/results/data.ts", web);
  const mirror = new URL(`benchmarks/${reportName}.gz`, web);
  if (check) {
    assert(
      (await readFile(target, "utf8")) === output,
      "generated data is stale; run node scripts/sync-results.mjs",
    );
    assert(
      sha256(gunzipSync(await readFile(mirror))) === data.sourceSha256,
      "pinned container input differs from the authoritative report",
    );
  } else {
    await mkdir(new URL("benchmarks/", web), { recursive: true });
    if (fileURLToPath(source.path) !== fileURLToPath(mirror)) {
      if (source.compressed) await copyFile(source.path, mirror);
      else await writeFile(mirror, gzipSync(source.raw));
    }
    await writeFile(target, output);
  }
  console.log(
    `Results data: ${data.rows.length} validated pipelines from ${data.date}`,
  );
}
if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)
  await syncResults(process.argv.includes("--check"));
