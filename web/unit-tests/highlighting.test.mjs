import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { highlightPassage } from "../src/features/search/lib/highlighting.ts";

test("highlights literal Unicode words without changing the retained passage", () => {
  const text =
    "Dense retrieval, dense representations, and café studies. Densely is different.";
  const parts = highlightPassage(text, "DENSE café dense");
  assert.equal(parts.map((part) => part.text).join(""), text);
  assert.deepEqual(
    parts.filter((part) => part.highlighted).map((part) => part.text),
    ["Dense", "dense", "café"],
  );
});
test("empty and punctuation-only queries preserve a plain text node", () => {
  for (const query of ["", "  ", "*** [] () +? "])
    assert.deepEqual(highlightPassage("<em>text</em>", query), [
      { text: "<em>text</em>", highlighted: false },
    ]);
});
test("passage HTML and event handlers remain escaped text, including highlighted fragments", () => {
  const text =
    '<img src=x onerror="window.injected=true"><script>alert(1)</script> retrieval';
  const parts = highlightPassage(text, "script img retrieval");
  const rendered = renderToStaticMarkup(
    createElement(
      "p",
      null,
      parts.map((part, index) =>
        part.highlighted
          ? createElement("mark", { key: index }, part.text)
          : part.text,
      ),
    ),
  );
  assert.equal(parts.map((part) => part.text).join(""), text);
  assert.ok(!rendered.includes("<img"));
  assert.ok(!rendered.includes("<script"));
  assert.ok(rendered.includes("&lt;"));
  assert.ok(rendered.includes("<mark>retrieval</mark>"));
});
test("punctuation in queries cannot become a regular expression or create empty matches", () => {
  const parts = highlightPassage(
    "A C++ study (2024) contrasts dense retrieval.",
    "C++ (2024) .* dense",
  );
  assert.deepEqual(
    parts.filter((part) => part.highlighted).map((part) => part.text),
    ["C", "2024", "dense"],
  );
  assert.ok(parts.every((part) => part.text.length));
});
