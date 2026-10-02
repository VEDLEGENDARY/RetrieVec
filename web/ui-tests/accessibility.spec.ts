import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("main views and command dialog have no serious automated accessibility violations", async ({
  page,
}) => {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: path.endsWith("/me")
        ? { principal_id: "owner", csrf_token: "token" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "one",
                title: "Papers",
                visibility: "private",
                can_manage: true,
                active_snapshot: "snapshot",
              },
            ]
          : path.endsWith("/runs")
            ? { items: [], next_cursor: null }
            : [],
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Papers", exact: true }),
  ).toBeVisible();
  async function scan() {
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      result.violations.filter(
        (item) => item.impact === "serious" || item.impact === "critical",
      ),
    ).toEqual([]);
  }
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    for (const name of ["Ask", "Sources", "Saved research"]) {
      await page
        .getByRole("navigation", { name: "Workspace sections" })
        .getByRole("button", { name, exact: true })
        .click();
      await scan();
    }
  }
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog")).toBeVisible();
  await scan();
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await scan();
});
