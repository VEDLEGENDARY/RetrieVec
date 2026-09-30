import { test, expect } from "@playwright/test";

test("OIDC, private upload, three-mode evidence, source access and second-user isolation", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Sign in to your workspace/ }).click();
  await page.getByRole("link", { name: "Sign in as a", exact: true }).click();
  await page.getByLabel("New collection").fill("Retrieval experiments");
  await page
    .getByRole("button", { name: "Create collection", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Retrieval experiments", exact: true }),
  ).toBeVisible();
  const sections = page.getByRole("navigation", { name: "Workspace sections" });
  await sections.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByLabel("Choose documents").setInputFiles({
    name: "private-evidence.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Dense retrieval matches semantic evidence. Sparse retrieval uses lexical matching. Hybrid retrieval combines both methods.",
    ),
  });
  await page
    .getByRole("button", { name: "Upload documents", exact: true })
    .click();
  await expect(
    page.getByText("Snapshot activated. Ready to search."),
  ).toBeVisible({ timeout: 90000 });
  await sections.getByRole("button", { name: "Ask", exact: true }).click();
  await page.getByLabel("Research question").fill("retrieval evidence");
  await page
    .getByRole("button", { name: "Search evidence →", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Hybrid · RRF" }),
  ).toBeVisible();
  await page
    .getByRole("region", { name: "Hybrid · RRF" })
    .getByRole("button")
    .first()
    .click();
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toBeVisible();
  const source = await page
    .getByRole("link", { name: "Open original source ↗" })
    .getAttribute("href");
  expect(source).toBeTruthy();
  const authorized = await page.request.get(source!, {
    headers: { Range: "bytes=0-4" },
  });
  expect(authorized.status()).toBe(206);
  expect(await authorized.text()).toBe("Dense");
  await page.getByRole("button", { name: "Answer", exact: true }).click();
  await page
    .getByLabel("Question for cited answer")
    .fill("What does dense retrieval match?");
  await page
    .getByRole("button", { name: "Generate cited answer", exact: true })
    .click();
  await expect(
    page.getByText("Research run: completed", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page
    .getByRole("button", { name: /Inspect citation/ })
    .first()
    .click();
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toContainText("Dense retrieval");
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toBeHidden();
  await expect(
    page.getByRole("button", { name: /Inspect citation/ }).first(),
  ).toBeFocused();
  const saved = await page.evaluate(async () => {
    const session = await (await fetch("/api/v1/me")).json();
    const collections = await (await fetch("/api/v1/collections")).json();
    const collection = collections.find(
      (item: { title: string }) => item.title === "Retrieval experiments",
    );
    const conversations = await (
      await fetch(
        `/api/v1/collections/${collection.collection_id}/conversations`,
      )
    ).json();
    const runs = await (
      await fetch(
        `/api/v1/conversations/${conversations[0].conversation_id}/runs`,
      )
    ).json();
    const run = runs[0];
    const exported = await (
      await fetch(`/api/v1/runs/${run.run_id}/exports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": session.csrf_token,
        },
        body: JSON.stringify({ format: "json" }),
      })
    ).json();
    return { run, exported, csrf: session.csrf_token };
  });
  await page.route(
    `**/api/v1/runs/${saved.run.run_id}`,
    async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          code: "service_unavailable",
          message: "Temporary outage",
        }),
      });
    },
    { times: 1 },
  );
  await expect(page.getByText(/Reconnecting to the saved run/)).toBeVisible({
    timeout: 10000,
  });
  await expect(
    page.getByRole("button", { name: "Export json", exact: true }),
  ).toBeHidden();
  await expect(
    page.getByText("Research run: completed", { exact: true }),
  ).toBeVisible();
  expect((await page.request.get(saved.exported.download_url)).status()).toBe(
    200,
  );
  const events = await page.request.get(
    `/api/v1/runs/${saved.run.run_id}/events`,
  );
  expect(await events.text()).toContain("event: completed");
  expect(
    (
      await page.request.get(`/api/v1/runs/${saved.run.run_id}/events?after=5`)
    ).status(),
  ).toBe(200);
  await page.getByText("Export answer", { exact: true }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export csv", exact: true }).click();
  expect((await downloadPromise).suggestedFilename()).toMatch(/\.csv$/);
  await page
    .getByRole("button", { name: "Replay pinned snapshot", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await page
    .getByRole("button", { name: "Saved research", exact: true })
    .click();
  await expect(
    page
      .getByRole("navigation", { name: "Saved research runs" })
      .getByRole("button", { name: /What does dense retrieval match/ }),
  ).toHaveCount(2);
  await expect(
    page.getByText("Research run: completed", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await sections.getByRole("button", { name: "Ask", exact: true }).click();
  await page
    .getByLabel("Question for cited answer")
    .fill("cancel this retrieval answer");
  await page
    .getByRole("button", { name: "Generate cited answer", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "cancel this retrieval answer",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Cancel run", exact: true }).click();
  await expect(
    page.getByText("Research run: cancelled", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Question for cited answer")
    .fill("no-evidence for quantum banana engines");
  await page
    .getByRole("button", { name: "Generate cited answer", exact: true })
    .click();
  await expect(
    page.getByText("I could not find this in your papers.", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page
    .getByLabel("Question for cited answer")
    .fill("provider-failure retrieval");
  await page
    .getByRole("button", { name: "Generate cited answer", exact: true })
    .click();
  await expect(
    page.getByText("Research run: failed", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await sections
    .getByRole("button", { name: "Saved research", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Saved research runs" })
    .getByRole("button", { name: /What does dense retrieval match/ })
    .last()
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/workspace-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/workspace-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByRole("link", { name: /Sign in to your workspace/ }).click();
  await page.getByRole("link", { name: "Sign in as b", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Start with a collection" }),
  ).toBeVisible();
  expect((await page.request.get(source!)).status()).toBe(404);
  for (const path of [
    `/api/v1/runs/${saved.run.run_id}`,
    `/api/v1/runs/${saved.run.run_id}/events`,
    `/api/v1/citations/${saved.run.result.evidence[0].citation_id}`,
    saved.exported.download_url,
  ]) {
    expect((await page.request.get(path)).status()).toBe(404);
  }
  await expect(
    page.getByRole("button", { name: /Retrieval experiments/ }),
  ).toHaveCount(0);
});
