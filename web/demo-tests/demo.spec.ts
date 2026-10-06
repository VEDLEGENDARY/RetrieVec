import { test, expect } from "@playwright/test";
import { randomBytes } from "node:crypto";

test("real Keycloak sign-in, preloaded hybrid search and sign-out", async ({
  page,
}) => {
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
  await page.screenshot({
    path: "test-results/demo-hybrid.png",
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Sign in to your workspace/ }),
  ).toBeVisible();
});
