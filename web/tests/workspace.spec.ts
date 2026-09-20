import { test, expect } from "@playwright/test";

test("OIDC, private upload, three-mode evidence, source access and second-user isolation", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Sign in to your workspace/ }).click();
  await page.getByRole("link", { name: "Sign in as a", exact: true }).click();
  await page.getByLabel("New collection").fill("Retrieval experiments");
  await page.getByRole("button", { name: "+ Create collection" }).click();
  await expect(
    page.getByRole("heading", { name: "Retrieval experiments", exact: true }),
  ).toBeVisible();
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
  await expect(
    page.getByRole("button", { name: /Retrieval experiments/ }),
  ).toHaveCount(0);
});
