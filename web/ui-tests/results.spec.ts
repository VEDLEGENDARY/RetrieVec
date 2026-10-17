import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("results route sorts actual benchmark values with scoped headers and direct SVG labels", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (
      request.url().includes("/api/") ||
      !request.url().startsWith("http://127.0.0.1:4173")
    )
      requests.push(request.url());
  });
  await page.goto("/results");
  await expect(
    page.getByRole("heading", { name: "Retrieval results", exact: true }),
  ).toBeVisible();
  const table = page.getByRole("table");
  await expect(table.locator("caption")).toContainText("October 1 benchmark");
  await expect(table.locator("thead th[scope=col]")).toHaveCount(7);
  await expect(table.locator("tbody th[scope=row]")).toHaveCount(10);
  await page
    .getByRole("button", { name: "Sort by nDCG@10", exact: true })
    .click();
  await expect(table.locator("thead th").nth(2)).toHaveAttribute(
    "aria-sort",
    "ascending",
  );
  await expect(table.locator("tbody tr").first()).toHaveAttribute(
    "data-dataset",
    "scidocs",
  );
  await expect(table.locator("tbody tr").first()).toHaveAttribute(
    "data-pipeline",
    "default_sparse",
  );
  await page.keyboard.press("Enter");
  await expect(table.locator("thead th").nth(2)).toHaveAttribute(
    "aria-sort",
    "descending",
  );
  await expect(table.locator("tbody tr").first()).toHaveAttribute(
    "data-pipeline",
    "tuned_hybrid",
  );
  await expect(table.locator("tbody tr").first()).toContainText("0.6847");
  await page
    .getByRole("button", { name: "Sort by p50 ms", exact: true })
    .click();
  await expect(table.locator("tbody tr").first()).toContainText("107.00");
  await expect(page.locator("svg [data-point]")).toHaveCount(10);
  await expect(
    page.getByText("SCIDOCS: Selected hybrid", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("complementary")).toContainText(
    "No model was trained",
  );
  await expect(page.getByRole("complementary")).toContainText(
    "No answer quality or PDF extraction evaluation",
  );
  expect(requests).toEqual([]);
});
for (const width of [1280, 390])
  test(`results are accessible in both themes at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/results");
    for (const theme of ["light", "dark"]) {
      await page.getByLabel("Appearance").selectOption(theme);
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
        path: info.outputPath(`results-${theme}.png`),
        fullPage: true,
      });
    }
  });
