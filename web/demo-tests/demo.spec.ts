import { test, expect, type Page } from "@playwright/test";
import { randomBytes } from "node:crypto";

async function register(page: Page) {
  await page.goto("/");
  await page.getByRole("link", { name: /Sign in to your workspace/ }).click();
  await page.getByRole("link", { name: "Register", exact: true }).click();
  const user = "demo-check-" + randomBytes(6).toString("hex");
  const password = randomBytes(24).toString("base64url");
  await page.locator("#username").fill(user);
  await page.locator("#email").fill(user + "@example.test");
  await page.locator("#firstName").fill("Demo");
  await page.locator("#lastName").fill("Check");
  await page.locator("#password").fill(password);
  await page.locator("#password-confirm").fill(password);
  await page.getByRole("button", { name: "Register", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /SciFact starter/ }),
  ).toBeVisible();
}

test("real Keycloak sign-in, preloaded hybrid search and sign-out", async ({
  page,
}, info) => {
  await register(page);
  await expect(
    page.getByRole("button", { name: "Find passages", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByText(
      "No answer provider configured. Use Find passages to search; ask the workspace operator to configure cited answers.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByLabel("Research question").fill("cancer");
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/search") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  const result = await (await response).json();
  expect(result.snapshot_id).toMatch(/^rs_[0-9a-f]{64}$/);
  expect(result.results.hybrid.hits.length).toBeGreaterThan(0);
  expect(
    result.results.hybrid.hits.every(
      (hit: { chunk_id: string; paper_id: string }) =>
        typeof hit.chunk_id === "string" &&
        typeof hit.paper_id === "string" &&
        hit.paper_id.startsWith("scifact-"),
    ),
  ).toBe(true);
  await expect(page.getByText(/unique passages/)).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await expect(page.locator(".collection-header")).toBeInViewport();
  await page.screenshot({
    path: info.outputPath("demo-hybrid.png"),
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Sign in to your workspace/ }),
  ).toBeVisible();
});

test("real private paper upload, library filtering, original source and search handoff", async ({
  page,
}) => {
  test.setTimeout(120000);
  await register(page);
  await page
    .getByLabel("New collection", { exact: true })
    .fill("Synthetic paper flow check");
  await page
    .locator(".new-collection")
    .getByRole("button", { name: "Create collection" })
    .click();
  await expect(page).toHaveURL(/view=sources/);
  const methods =
    "Synthetic interface verification paper. The method uses a controlled comparison of semantic retrieval and lexical matching. This fixture is not scientific evidence.";
  await page.getByLabel("Choose documents", { exact: true }).setInputFiles([
    {
      name: "method_100%.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(methods),
    },
    {
      name: "findings.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "Synthetic findings for interface verification only. No scientific claim is made.",
      ),
    },
  ]);
  await page
    .getByRole("button", { name: "Upload documents", exact: true })
    .click();
  const original = page.getByRole("link", {
    name: "Open original method_100%.txt in a new tab",
  });
  await expect(original).toBeVisible({ timeout: 90000 });
  const source = await page.request.get((await original.getAttribute("href"))!);
  expect(source.status()).toBe(200);
  expect(await source.text()).toBe(methods);
  expect(source.headers()["cache-control"]).toBe("no-store");
  await page.getByLabel("Find an uploaded paper").fill("%");
  await expect(
    page.getByRole("heading", { name: "method_100%.txt", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "findings.txt", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Search your papers", exact: true })
    .click();
  await page
    .getByLabel("Research question", { exact: true })
    .fill("controlled comparison of semantic retrieval");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await expect(page.getByText(/unique passages/)).toBeVisible({
    timeout: 20000,
  });
  await expect(
    page.getByRole("button", { name: /^method_100%/ }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Sign in to your workspace" }),
  ).toBeVisible();
});
