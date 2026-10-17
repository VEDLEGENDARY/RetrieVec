import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const file = {
  source_id: "source",
  name: "Retained paper.txt",
  size_bytes: 128,
  media_type: "text/plain",
  state: "running",
  stage: "extract",
  stage_scope: "batch",
  provenance: null,
};
const provenance = {
  source_sha256: "a".repeat(64),
  extraction_version: "utf8-text-v1",
  extractors: [{ name: "UTF-8 text reader", revision: "v1" }],
  ocr_used: false,
  derivations: ["source_text"],
};
const job = {
  job_id: "job",
  collection_id: "one",
  state: "running",
  stage: "extract",
  progress: { files: [file] },
  output_snapshot: null,
  error_code: null,
};
async function sources(page: Page, initialJobs: unknown[] = []) {
  let jobs = initialJobs;
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "upload-fixture", csrf_token: "upload-csrf" };
    else if (path === "/api/v1/collections")
      json = [
        {
          collection_id: "one",
          title: "Upload collection",
          can_manage: true,
          active_snapshot: "snapshot",
          visibility: "private",
        },
      ];
    else if (path.endsWith("/jobs")) json = jobs;
    else if (path.endsWith("/papers")) json = { items: [], next_cursor: null };
    else if (path.endsWith("/runs")) json = { items: [], next_cursor: null };
    return route.fulfill({ json });
  });
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Workspace sections" })
    .getByRole("button", { name: "Sources", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Add to your sources" }),
  ).toBeVisible();
  return {
    setJobs: (value: unknown[]) => {
      jobs = value;
    },
  };
}
test("review queue blocks invalid files, shows type and size, and supports remove and drop", async ({
  page,
}) => {
  await sources(page);
  let submissions = 0;
  await page.route("**/uploads", (route) => {
    submissions++;
    return route.fulfill({ json: job });
  });
  await page.getByLabel("Choose documents").setInputFiles([
    {
      name: "paper.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Retained paper"),
    },
    {
      name: "unsafe.exe",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("Invalid"),
    },
    { name: "empty.md", mimeType: "text/markdown", buffer: Buffer.from("") },
  ]);
  const queue = page.locator(".upload-queue");
  await expect(queue.locator("li")).toHaveCount(3);
  await expect(queue).toContainText("text/plain");
  await expect(queue).toContainText("KiB");
  await expect(queue).toContainText("Use a PDF, text, or Markdown file.");
  await expect(queue).toContainText("This file is empty.");
  const upload = page.getByRole("button", {
    name: "Upload documents",
    exact: true,
  });
  await expect(upload).toBeDisabled();
  await page
    .getByRole("button", { name: "Remove unsafe.exe", exact: true })
    .press("Enter");
  await expect(upload).toBeDisabled();
  await page
    .getByRole("button", { name: "Remove empty.md", exact: true })
    .press("Enter");
  await expect(upload).toBeEnabled();
  expect(submissions).toBe(0);
  const transfer = await page.evaluateHandle(() => {
    const value = new DataTransfer();
    value.items.add(
      new File(["Research note"], "note.md", { type: "text/markdown" }),
    );
    return value;
  });
  await page
    .locator(".upload-dropzone")
    .dispatchEvent("drop", { dataTransfer: transfer });
  await expect(queue.locator("li")).toHaveCount(2);
  await expect(queue).toContainText("Passes local file checks");
  await transfer.dispose();
});
test("retry of an unchanged batch reuses the request key and batch changes replace it", async ({
  page,
}) => {
  await sources(page);
  const keys: string[] = [],
    bodies: Buffer[] = [];
  await page.route("**/uploads", (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    bodies.push(route.request().postDataBuffer()!);
    expect(route.request().headers()["x-csrf-token"]).toBe("upload-csrf");
    return route.fulfill({
      status: 503,
      json: { code: "upload_unconfirmed", message: "Response was lost" },
    });
  });
  await page.getByLabel("Choose documents").setInputFiles({
    name: "paper.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Original batch"),
  });
  await page
    .getByRole("button", { name: "Upload documents", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retry upload", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Refresh upload status", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Retry upload", exact: true })
    .press("Enter");
  await expect.poll(() => keys.length).toBe(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);
  expect(
    bodies.every((value) => value.includes(Buffer.from("Original batch"))),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Remove paper.txt", exact: true })
    .click();
  await page.getByLabel("Choose documents").setInputFiles({
    name: "changed.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Changed batch"),
  });
  await page
    .getByRole("button", { name: "Upload documents", exact: true })
    .click();
  await expect.poll(() => keys.length).toBe(3);
  expect(keys[2]).not.toBe(keys[0]);
});
test("per-file batch progress becomes retained extractor and OCR provenance", async ({
  page,
}) => {
  const fixture = await sources(page, [job]);
  await expect(
    page.getByRole("progressbar", { name: "Ingestion for Retained paper.txt" }),
  ).toBeVisible();
  await expect(page.locator(".ingestion-file")).toContainText(
    "Batch stage: Extracting text",
  );
  fixture.setJobs([
    {
      ...job,
      state: "succeeded",
      stage: "activate",
      output_snapshot: "snapshot",
      progress: {
        files: [{ ...file, state: "succeeded", stage: "activate", provenance }],
      },
    },
  ]);
  await expect(page.locator(".ingestion-file")).toContainText(
    "Ready to search",
    { timeout: 10000 },
  );
  await expect(page.locator(".ingestion-file")).toContainText(
    "UTF-8 text reader (v1)",
  );
  await expect(page.locator(".ingestion-file")).toContainText("Not used");
  await expect(page.locator(".ingestion-file code").last()).toHaveText(
    "a".repeat(64),
  );
  await expect(page.getByRole("progressbar")).toHaveCount(0);
});
for (const width of [1440, 390])
  test(`upload queue and provenance pass axe in both themes at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    await sources(page, [
      {
        ...job,
        state: "succeeded",
        progress: { files: [{ ...file, state: "succeeded", provenance }] },
      },
    ]);
    await page.getByLabel("Choose documents").setInputFiles({
      name: "review.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Review"),
    });
    for (const theme of ["light", "dark"]) {
      if (width === 390)
        await page.getByRole("button", { name: "Open navigation" }).click();
      await page.getByLabel("Appearance").selectOption(theme);
      if (width === 390)
        await page.getByRole("button", { name: "Close navigation" }).click();
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze()
        ).violations,
      ).toEqual([]);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      await page.screenshot({
        path: info.outputPath(`uploads-${theme}.png`),
        fullPage: true,
      });
    }
  });
test("500 retained file rows remain responsive without virtualization", async ({
  page,
}, info) => {
  await sources(
    page,
    Array.from({ length: 50 }, (_, index) => ({
      ...job,
      job_id: `job-${index}`,
      state: "succeeded",
      progress: {
        files: Array.from({ length: 10 }, (_, position) => ({
          ...file,
          source_id: `${index}-${position}`,
          name: `Paper ${index}-${position}.txt`,
          provenance,
        })),
      },
    })),
  );
  await expect(page.locator(".ingestion-file")).toHaveCount(500);
  const elapsed = await page.evaluate(async () => {
    const start = performance.now();
    document.querySelector<HTMLInputElement>("#documents")!.focus();
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    return performance.now() - start;
  });
  await info.attach("large-list-response", {
    body: JSON.stringify({ fileRows: 500, focusToPaintMs: elapsed }),
    contentType: "application/json",
  });
  expect(elapsed).toBeLessThan(500);
  await expect(page.getByLabel("Choose documents")).toBeFocused();
});
