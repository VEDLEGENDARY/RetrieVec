import { test } from "node:test";
import assert from "node:assert/strict";
import {
  readSource,
  projectBenchmark,
  sha256,
} from "../scripts/sync-results.mjs";
const { raw } = await readSource();
const source = JSON.parse(raw);
test("results copy the recorded scores, cutoffs and source identities exactly", () => {
  const data = projectBenchmark(source, sha256(raw));
  assert.equal(data.rows.length, 10);
  for (const row of data.rows) {
    const run = source.datasets[row.dataset].runs[row.pipeline];
    assert.equal(row.ndcg10, run.metrics.ndcg);
    assert.equal(row.recall100, run.metrics.recall);
    assert.equal(row.mrr10, run.metrics.mrr);
    assert.equal(row.p50, run.latency_ms.p50);
    assert.equal(row.p95, run.latency_ms.p95);
    assert.equal(row.resultsSha256, run.results_sha256);
  }
});
test("the build rejects schema drift, incomplete evaluations and invalid metrics", () => {
  for (const mutate of [
    (value) => {
      value.unreviewed_field = true;
    },
    (value) => {
      delete value.datasets.scifact.runs.default_sparse.metrics.mrr;
    },
    (value) => {
      value.complete = false;
    },
    (value) => {
      value.datasets.scifact.runs.default_sparse.metrics.ndcg = 1.2;
    },
    (value) => {
      value.datasets.scidocs.runs.default_dense.latency_ms.p95 = -1;
    },
  ]) {
    const value = structuredClone(source);
    mutate(value);
    assert.throws(
      () => projectBenchmark(value, sha256(raw)),
      /Benchmark schema/,
    );
  }
});
test("dataset colors retain text contrast on both reading surfaces in both themes", async () => {
  const css = await (
    await import("node:fs/promises")
  ).readFile(new URL("../src/tokens.css", import.meta.url), "utf8");
  const pair = (name) =>
    css
      .match(
        new RegExp(
          `${name}:\\s*light-dark\\((#[a-f0-9]{6}),\\s*(#[a-f0-9]{6})\\)`,
        ),
      )
      .slice(1);
  const luminance = (hex) =>
    hex
      .slice(1)
      .match(/../g)
      .map((x) => parseInt(x, 16) / 255)
      .map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4))
      .reduce((sum, x, i) => sum + x * [0.2126, 0.7152, 0.0722][i], 0);
  for (const token of ["--dataset-scifact", "--dataset-scidocs"])
    for (const surface of ["--canvas", "--surface", "--subtle"])
      for (let theme = 0; theme < 2; theme++) {
        const foreground = luminance(pair(token)[theme]),
          background = luminance(pair(surface)[theme]);
        assert.ok(
          (Math.max(foreground, background) + 0.05) /
            (Math.min(foreground, background) + 0.05) >=
            4.5,
          `${token} on ${surface}, theme ${theme}`,
        );
      }
});
