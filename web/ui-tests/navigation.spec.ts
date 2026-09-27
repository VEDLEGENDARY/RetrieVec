import { test, expect } from "@playwright/test";

test("command navigation keeps query drafts and collection filtering works", async ({
  page,
}) => {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const data = path.endsWith("/me")
      ? { principal_id: "demo", csrf_token: "test" }
      : path === "/api/v1/collections"
        ? [
            {
              collection_id: "demo",
              title: "Retrieval literature",
              visibility: "private",
              can_manage: true,
              active_snapshot: "snapshot-demo",
            },
          ]
        : [];
    return route.fulfill({ json: data });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Retrieval literature", exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/workspace-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Quick actions" }).click();
  await page
    .getByRole("textbox", { name: "Find actions and collections" })
    .fill("Search");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByLabel("Research question")
    .fill("How does hybrid retrieval work?");
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByLabel("Research question")).toHaveValue(
    "How does hybrid retrieval work?",
  );
  await page.getByLabel("Find a collection").fill("missing");
  await expect(
    page.getByText("No collections match", { exact: false }),
  ).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/workspace-mobile.png", fullPage: true, animations: "disabled" });
});
