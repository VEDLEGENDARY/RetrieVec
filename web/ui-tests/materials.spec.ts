import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function workspace(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/papers"))
      return route.fulfill({
        json: { items: [], next_cursor: null },
      });
    return route.fulfill({
      json: path.endsWith("/me")
        ? { principal_id: "material-fixture", csrf_token: "fixture" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "one",
                title: "Research materials",
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
    page.getByRole("heading", { name: "Research materials", exact: true }),
  ).toBeVisible();
}

test("material rim responds to pointer input while evidence surfaces stay solid", async ({
  page,
}) => {
  await page.emulateMedia({
    reducedMotion: "no-preference",
    forcedColors: "none",
  });
  const client = await page.context().newCDPSession(page);
  await client.send("Emulation.setEmulatedMedia", {
    features: [
      { name: "prefers-reduced-transparency", value: "no-preference" },
      { name: "prefers-reduced-motion", value: "no-preference" },
    ],
  });
  await workspace(page);
  const header = page.locator(".collection-header");
  const rect = (await header.boundingBox())!;
  await page.mouse.move(rect.x + rect.width * 0.75, rect.y + rect.height * 0.5);
  const light = await header.evaluate((node) =>
    node.style.getPropertyValue("--light-x"),
  );
  expect(
    parseFloat(light),
    JSON.stringify(
      await page.evaluate(() => ({
        motion: matchMedia("(prefers-reduced-motion: reduce)").matches,
        transparency: matchMedia("(prefers-reduced-transparency: reduce)")
          .matches,
      })),
    ),
  ).toBeCloseTo(75, 0);
  await expect(
    page.getByRole("heading", { name: "Research materials", exact: true }),
  ).toBeVisible();
  const alpha = await page
    .locator(".collection-header-content")
    .evaluate((node) => getComputedStyle(node).backgroundColor);
  expect(alpha).toMatch(/^rgb\(/);
  await page.mouse.move(0, 0);
  expect(
    await header.evaluate((node) => node.style.getPropertyValue("--light-x")),
  ).toBe("");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.mouse.move(rect.x + rect.width * 0.75, rect.y + rect.height * 0.5);
  expect(
    await header.evaluate((node) => node.style.getPropertyValue("--light-x")),
  ).toBe("");
});

test("materials flatten for transparency and contrast preferences", async ({
  page,
}) => {
  await workspace(page);
  const client = await page.context().newCDPSession(page);
  for (const preference of [
    { name: "prefers-reduced-transparency", value: "reduce" },
    { name: "forced-colors", value: "active" },
  ]) {
    await client.send("Emulation.setEmulatedMedia", { features: [preference] });
    expect(
      await page
        .locator(".collection-header")
        .evaluate((node) => getComputedStyle(node).backdropFilter),
    ).toBe("none");
    expect(
      await page
        .locator(".collection-header")
        .evaluate((node) => getComputedStyle(node, "::before").display),
    ).toBe("none");
    await page.getByRole("button", { name: "Sources", exact: true }).focus();
    const focus = await page
      .getByRole("button", { name: "Sources", exact: true })
      .evaluate((node) => getComputedStyle(node).outlineStyle);
    expect(focus).not.toBe("none");
  }
});

test("all destinations reflow at 320px with doubled text in both themes", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await workspace(page);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
    for (const destination of ["Ask", "Sources", "Saved research"]) {
      const button = page
        .getByRole("navigation", { name: "Workspace sections" })
        .getByRole("button", { name: destination, exact: true });
      await button.click();
      await expect(button).toHaveAttribute("aria-current", "page");
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(320);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(result.violations).toEqual([]);
      await page.screenshot({
        path: info.outputPath(`text-reflow-${destination}-${colorScheme}.png`),
        fullPage: true,
        animations: "disabled",
      });
    }
  }
});
