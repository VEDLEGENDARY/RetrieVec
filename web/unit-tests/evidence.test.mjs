import { test } from "node:test";
import assert from "node:assert/strict";
import {
  citationText,
  passageIdentity,
  passages,
  queryKey,
  shortlistExport,
  sourceHash,
  validateSearch,
} from "../src/features/search/lib/evidence.ts";

const hit = (id, rank, text = "Retained evidence") => ({
  chunk_id: id,
  title: `Paper ${id}`,
  text,
  rank,
  source_id: null,
  source_sha256: "a".repeat(64),
  page_range: [2, 3],
  bm25_score: 2,
  cosine_score: 0.8,
  rrf_score: 0.02,
});
const result = {
  snapshot_id: "snapshot",
  collection_id: "collection",
  query: "evidence",
  mode: "free_text",
  results: {
    sparse: {
      hits: [hit("a", 1), hit("b", 2)],
      configuration: {},
      total_matches: 2,
    },
    dense: {
      hits: [hit("b", 1), hit("a", 2)],
      configuration: {},
      total_matches: 2,
    },
    hybrid: { hits: [hit("a", 1)], configuration: {}, total_matches: 1 },
  },
};
test("filtering is literal and method ordering comes from actual ranks", () => {
  assert.deepEqual(
    passages(result, "dense", "", "active").map((item) => item.hit.chunk_id),
    ["b", "a"],
  );
  assert.deepEqual(
    passages(result, "hybrid", "paper B", "all").map(
      (item) => item.hit.chunk_id,
    ),
    ["b"],
  );
  assert.equal(passages(result, "sparse", ".*", "all").length, 0);
  assert.equal(passages(result, "sparse", "", "hybrid").length, 1);
  const denseFilter = passages(result, "hybrid", "", "dense");
  assert.deepEqual(
    denseFilter.map((item) => item.hit.chunk_id),
    ["b", "a"],
  );
  assert.equal(denseFilter[0].method, "dense");
  assert.equal(denseFilter[0].ranks.dense.score, 0.8);
  assert.deepEqual(passages(result, "dense", "", "active")[0].ranks.dense, {
    rank: 1,
    score: 0.8,
    label: "Cosine",
  });
});
test("cache identities separate snapshots, syntax, sections and reranking", () => {
  const spec = {
    snapshot: "one",
    query: " evidence ",
    mode: "free_text",
    section: "",
    rerank: false,
  };
  assert.equal(queryKey(spec), queryKey({ ...spec, query: "evidence" }));
  for (const next of [
    { snapshot: "two" },
    { mode: "structured" },
    { section: "methods" },
    { rerank: true },
  ])
    assert.notEqual(queryKey(spec), queryKey({ ...spec, ...next }));
  assert.notEqual(passageIdentity("one", "a"), passageIdentity("two", "a"));
});
test("export retains questions, content, method ranks and snapshot identities", () => {
  const passage = passages(result, "dense", "", "active")[0];
  const saved = {
    hit: passage.hit,
    snapshot_id: result.snapshot_id,
    query: "Original question",
    methods: passage.methods,
    ranks: passage.ranks,
  };
  const exported = shortlistExport(
    "collection",
    [saved],
    "2026-10-14T12:00:00Z",
  );
  assert.equal(exported.schema_version, 1);
  assert.equal(exported.collection_id, "collection");
  assert.equal(exported.passages[0].query, "Original question");
  assert.equal(exported.passages[0].snapshot_id, "snapshot");
  assert.equal(exported.passages[0].hit.text, "Retained evidence");
  assert.deepEqual(exported.passages[0].methods, ["sparse", "dense"]);
  assert.equal(exported.passages[0].ranks.dense.rank, 1);
  assert.equal(exported.exported_at, "2026-10-14T12:00:00Z");
  assert.notEqual(exported.passages[0].hit, saved.hit);
  assert.throws(
    () => shortlistExport("collection", Array(7).fill(saved)),
    /six/,
  );
});
test("hash display only accepts an actual source hash and copy retains provenance", () => {
  assert.equal(sourceHash(hit("a", 1)), "a".repeat(64));
  assert.equal(
    sourceHash({
      ...hit("a", 1),
      source_sha256: undefined,
      source_id: "b".repeat(64),
    }),
    null,
  );
  assert.match(
    citationText(hit("a", 1), "snapshot", "Question"),
    /Snapshot: snapshot/,
  );
  assert.match(
    citationText(hit("a", 1), "snapshot", "Question"),
    /Question: Question/,
  );
});
test("malformed and cross-collection responses cannot become cached evidence", () => {
  assert.equal(validateSearch(result, "collection"), result);
  for (const value of [
    null,
    [],
    { ...result, snapshot_id: "" },
    { ...result, collection_id: "other" },
    { ...result, results: {} },
    { ...result, results: { hybrid: { hits: [hit("x", NaN)] } } },
  ])
    assert.throws(() => validateSearch(value, "collection"));
});
