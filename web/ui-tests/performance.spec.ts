import { test, expect } from "@playwright/test";
import { writeFile } from "node:fs/promises";

test("local performance baseline and recorder privacy", async ({
  page,
}, testInfo) => {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const json =
      path === "/api/v1/me"
        ? { principal_id: "private-user", csrf_token: "secret-token" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "private-collection",
                title: "Private paper title",
                visibility: "private",
                active_snapshot: "private-snapshot",
                can_manage: true,
              },
            ]
          : path === "/api/v1/search"
            ? {
                collection_id: "private-collection",
                snapshot_id: "private-snapshot",
                query: "Private question",
                mode: "free_text",
                results: {
                  hybrid: { hits: [], total_matches: 0, configuration: {} },
                },
              }
            : [];
    return route.fulfill({ json });
  });
  const runs: unknown[] = [];
  // Alternate configurations to reduce warm-cache/order bias. First pair is warmup.
  for (let i = 0; i < 12; i++) {
    const enabled = i % 2 === 1;
    await page.goto(enabled ? "/?performance=1" : "/");
    await expect(
      page.getByRole("heading", { name: "Private paper title", exact: true }),
    ).toBeVisible();
    const readyObserved = await page.evaluate(() => performance.now());
    await page
      .getByRole("navigation", { name: "Workspace sections" })
      .getByRole("button", { name: "Ask", exact: true })
      .click();
    await page.getByLabel("Research question").fill("Private question");
    await page
      .getByRole("button", { name: "Search evidence →", exact: true })
      .click();
    await expect(
      page.getByText("No matching passages. Try a different question."),
    ).toBeVisible();
    const recorder = await page.evaluate(() =>
      window.retrievecPerformance?.snapshot(),
    );
    if (!enabled) expect(recorder).toBeUndefined();
    else {
      expect(recorder?.some((sample) => sample.metric === "app.ready")).toBe(
        true,
      );
      expect(
        recorder?.some(
          (sample) =>
            sample.metric === "retrieval.response" && sample.outcome === "ok",
        ),
      ).toBe(true);
      expect(JSON.stringify(recorder)).not.toMatch(
        /private|secret|question|snapshot/i,
      );
      expect(
        await page.evaluate(() => {
          window.retrievecPerformance?.clear();
          return window.retrievecPerformance?.snapshot();
        }),
      ).toEqual([]);
    }
    if (i >= 2) runs.push({ enabled, readyObserved, samples: recorder });
  }
  const reportPath = testInfo.outputPath("ui-baseline.json");
  await writeFile(
    reportPath,
    JSON.stringify(
      {
        kind: "synthetic-http-development-ui",
        browser: await page.evaluate(() => navigator.userAgent),
        viewport: page.viewportSize(),
        runs,
      },
      null,
      2,
    ),
  );
  await testInfo.attach("ui-baseline.json", {
    path: reportPath,
    contentType: "application/json",
  });
});
