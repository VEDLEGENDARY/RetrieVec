import { test, expect } from "@playwright/test";

test("section filter is explicit, opt-in, and sent with passage searches", async ({
  page,
}) => {
  const submitted: Record<string, unknown>[] = [];
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "fixture", csrf_token: "fixture" };
    if (path === "/api/v1/collections")
      json = [
        {
          collection_id: "one",
          title: "Fixture collection",
          visibility: "private",
          active_snapshot: "snapshot",
          can_manage: true,
        },
      ];
    if (path === "/api/v1/search") {
      submitted.push(route.request().postDataJSON());
      json = {
        snapshot_id: "snapshot",
        results: { hybrid: { hits: [], total_matches: 0, configuration: {} } },
      };
    }
    return route.fulfill({ json });
  });
  await page.goto("/");
  await page.getByLabel("Research question").fill("A question");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0]).not.toHaveProperty("section");
  await page.getByText("More section filters", { exact: true }).click();
  await expect(
    page
      .locator(".field-description:visible")
      .filter({ hasText: "Filters the retrieved candidate pool" }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Paper section" })
    .selectOption("methods");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await expect.poll(() => submitted.length).toBe(2);
  expect(submitted[1].section).toBe("methods");
});
