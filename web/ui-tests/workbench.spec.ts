import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

const hits = [
  {
    rank: 1,
    chunk_id: "passage-a",
    title: "Learning dense representations",
    text: "Dense retrieval learns semantic representations from paired questions and passages.",
    source_id: null,
    page_range: [3, 4],
    bm25_score: 2.3,
    cosine_score: 0.85,
    rrf_score: 0.02,
  },
  {
    rank: 2,
    chunk_id: "passage-b",
    title: "Lexical baselines",
    text: "Sparse retrieval uses exact term overlap. Hybrid retrieval combines lexical and dense evidence.",
    source_id: null,
    page_range: [7, 7],
    bm25_score: 1.9,
    cosine_score: 0.72,
    rrf_score: 0.018,
  },
];
async function openWorkbench(page: Page, view: "Search" | "Sources") {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "test", csrf_token: "test-token" };
    if (path === "/api/v1/collections")
      json = ["Methods", "Other papers"].map((title, index) => ({
        collection_id: `collection-${index}`,
        title,
        visibility: "private",
        active_snapshot: "snapshot-a",
        can_manage: true,
      }));
    if (path === "/api/v1/search") {
      const body = route.request().postDataJSON();
      json = {
        collection_id: body.collection_id,
        snapshot_id: "snapshot-a",
        query: body.query,
        mode: body.mode,
        results: Object.fromEntries(
          ["sparse", "dense", "hybrid"].map((method) => [
            method,
            { hits, total_matches: 20, configuration: {} },
          ]),
        ),
      };
    }
    return route.fulfill({ json });
  });
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Workspace sections" })
    .getByRole("button", {
      name: view === "Search" ? "Ask" : view,
      exact: true,
    })
    .click();
}

test("filter, inspect, shortlist and export preserve evidence provenance", async ({
  page,
}) => {
  await openWorkbench(page, "Search");
  await page
    .getByLabel("Research question")
    .fill("Compare lexical and dense retrieval");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await expect(page.getByText("2 unique passages")).toBeVisible();
  await page.getByText("More result options", { exact: true }).click();
  await page.getByLabel("Show retrieval method").selectOption("hybrid");
  await page.getByLabel("Filter returned passages").fill("Lexical baselines");
  const ranking = page.getByRole("region", { name: "Hybrid · RRF" });
  await expect(ranking.locator("li")).toHaveAttribute("value", "2");
  const hit = ranking.getByRole("button", { name: /Lexical baselines/ });
  await hit.click();
  const inspector = page.getByRole("complementary", {
    name: "Evidence inspector",
  });
  await expect(inspector).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(hit).toBeFocused();
  await ranking.getByRole("button", { name: "Shortlist passage" }).click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Passage added to the evidence shortlist." }),
  ).toBeVisible();
  await page.getByText("More evidence options", { exact: true }).click();
  await page.locator("#passage-shortlist > summary").click();
  await expect(page.locator(".passage-board article")).toHaveCount(1);
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export evidence" }).click();
  const download = await downloadEvent;
  const exported = JSON.parse(await readFile((await download.path())!, "utf8"));
  expect(exported.collection_id).toBe("collection-0");
  expect(exported.passages[0].snapshot_id).toBe("snapshot-a");
  expect(exported.passages[0].hit.chunk_id).toBe("passage-b");
  expect(exported.passages[0].query).toBe(
    "Compare lexical and dense retrieval",
  );
  expect(exported.passages[0].methods).toEqual(["sparse", "dense", "hybrid"]);
  await page
    .getByRole("button", { name: "Remove Lexical baselines from shortlist" })
    .click();
  await expect(page.locator(".passage-board article")).toHaveCount(0);
  await page.getByRole("button", { name: "Undo remove passage" }).click();
  await expect(page.locator(".passage-board article")).toHaveCount(1);
  await page.getByLabel("Filter returned passages").fill("");
  await ranking
    .getByRole("button", { name: "Shortlist passage" })
    .first()
    .click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/evidence-workbench.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/evidence-mobile-dark.png",
    fullPage: true,
    animations: "disabled",
  });
});

test("shortlist enforces its comparison limit and frees slots on removal", async ({
  page,
}) => {
  await openWorkbench(page, "Search");
  await page.route("**/api/v1/search", (route) =>
    route.fulfill({
      json: {
        collection_id: "collection-0",
        snapshot_id: "snapshot-a",
        query: "Evidence",
        mode: "free_text",
        results: {
          sparse: {
            configuration: {},
            total_matches: 7,
            hits: Array.from({ length: 7 }, (_, index) => ({
              ...hits[0],
              rank: index + 1,
              chunk_id: `passage-${index}`,
              title: `Paper ${index + 1}`,
            })),
          },
        },
      },
    }),
  );
  await page.getByLabel("Research question").fill("Evidence");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await page.getByText("More evidence options", { exact: true }).click();
  const controls = page.getByRole("button", { name: "Shortlist passage" });
  for (let index = 0; index < 7; index++) await controls.nth(index).click();
  await expect(page.locator(".count-pill")).toHaveText("6/6");
  await expect(
    page.getByText("Your shortlist has six passages.", { exact: false }),
  ).toBeVisible();
  await controls.first().click();
  await expect(page.locator(".count-pill")).toHaveText("5/6");
  await controls.nth(6).click();
  await expect(controls.nth(6)).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".count-pill")).toHaveText("6/6");
});

test("recent searches restore drafts and collection changes clear the shortlist", async ({
  page,
}) => {
  await openWorkbench(page, "Search");
  await page.getByLabel("Research question").fill("Original question");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Sparse · BM25" })
    .getByRole("button", { name: "Shortlist passage" })
    .first()
    .click();
  await page.getByLabel("Research question").fill("Unsaved draft");
  await page.getByText("More evidence options", { exact: true }).click();
  await page.locator("#recent-searches > summary").click();
  await page.getByRole("button", { name: /Original question/ }).click();
  await expect(page.getByLabel("Research question")).toHaveValue(
    "Original question",
  );
  await page
    .getByRole("navigation", { name: "Collections" })
    .getByRole("button", { name: /Other papers/ })
    .click();
  await page
    .getByRole("navigation", { name: "Workspace sections" })
    .getByRole("button", { name: "Ask", exact: true })
    .click();
  await expect(page.locator(".count-pill")).toHaveText("0/6");
  await expect(page.getByLabel("Research question")).toHaveValue("");
});

test("upload review rejects unsupported files and keeps the retry key for an unchanged batch", async ({
  page,
}) => {
  await openWorkbench(page, "Sources");
  const input = page.getByLabel("Choose documents");
  await input.setInputFiles([
    {
      name: "notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Useful research notes"),
    },
    {
      name: "program.exe",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("invalid"),
    },
  ]);
  const upload = page.getByRole("button", {
    name: "Upload documents",
    exact: true,
  });
  await expect(upload).toBeDisabled();
  await expect(
    page.getByText("Use a PDF, text, or Markdown file."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Remove program.exe" }).click();
  await expect(upload).toBeEnabled();
  await page.getByRole("button", { name: "Undo remove document" }).click();
  await expect(upload).toBeDisabled();
  await page.getByRole("button", { name: "Remove program.exe" }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/upload-review.png",
    fullPage: true,
  });
  const keys: string[] = [];
  await page.route("**/uploads", (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    return keys.length === 1
      ? route.fulfill({
          status: 503,
          json: { code: "unavailable", message: "Try again" },
        })
      : route.fulfill({
          json: {
            job_id: "job-a",
            state: "queued",
            stage: "queued",
            progress: {},
            output_snapshot: null,
          },
        });
  });
  await upload.click();
  await expect(
    page.getByText("Upload was not confirmed.", { exact: false }),
  ).toBeVisible();
  await upload.click();
  await expect(
    page.getByText("Accepted for processing.", { exact: false }),
  ).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);
});
