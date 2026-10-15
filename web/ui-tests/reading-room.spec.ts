import { test, expect, type Page } from "@playwright/test";

// Synthetic interface fixtures. These make no retrieval quality claims.
const passage = "A retained passage for interface verification. ".repeat(12);
async function workspace(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const hit = (id: string, rank: number) => ({
      chunk_id: id,
      rank,
      title: `Synthetic paper ${id}`,
      text: passage,
      source_id: null,
      page_range: [1, 1],
      bm25_score: 1.5,
      cosine_score: 0.5,
      rrf_score: 0.012,
    });
    return route.fulfill({
      json: path.endsWith("/me")
        ? { principal_id: "reading-room", csrf_token: "fixture" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "one",
                title: "Reading room",
                visibility: "private",
                can_manage: true,
                active_snapshot: "snapshot",
              },
            ]
          : path.endsWith("/papers") || path.endsWith("/runs")
            ? { items: [], next_cursor: null }
            : path.endsWith("/search")
              ? {
                  snapshot_id: "snapshot",
                  collection_id: "one",
                  query: "Synthetic query",
                  mode: "free_text",
                  results: {
                    sparse: {
                      hits: [hit("a", 1), hit("b", 2)],
                      total_matches: 2,
                      configuration: {},
                    },
                    dense: {
                      hits: [hit("b", 1), hit("a", 2)],
                      total_matches: 2,
                      configuration: {},
                    },
                    hybrid: {
                      hits: [hit("a", 1), hit("b", 2)],
                      total_matches: 2,
                      configuration: {},
                    },
                  },
                }
              : [],
    });
  });
  await page.goto("/");
  await expect(page.getByLabel("Research question")).toBeVisible();
}

test("appearance follows the system, persists manual choices, and synchronizes tabs", async ({
  page,
  context,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await workspace(page);
  const root = page.locator("html");
  const choice = page.getByLabel("Appearance");
  await expect(root).toHaveCSS("background-color", "rgb(13, 26, 28)");
  await choice.selectOption("light");
  await expect(root).toHaveCSS("background-color", "rgb(233, 237, 232)");
  await page.reload();
  await expect(choice).toHaveValue("light");
  await page.emulateMedia({ colorScheme: "light" });
  await choice.selectOption("dark");
  await expect(root).toHaveCSS("background-color", "rgb(13, 26, 28)");
  const second = await context.newPage();
  await workspace(second);
  await expect(second.getByLabel("Appearance")).toHaveValue("dark");
  await second.getByLabel("Appearance").selectOption("light");
  await expect(choice).toHaveValue("light");
  await second.close();
  await choice.selectOption("system");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(root).toHaveCSS("background-color", "rgb(13, 26, 28)");
  await expect
    .poll(() =>
      page.locator('meta[name="theme-color"]').getAttribute("content"),
    )
    .toBe("rgb(13, 26, 28)");
  expect(
    await page.evaluate(() => localStorage.getItem("retrievec.theme")),
  ).toBeNull();
});

test("manual appearance works when device storage is blocked", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("Blocked", "SecurityError");
      },
    });
  });
  await workspace(page);
  await page.getByLabel("Appearance").selectOption("dark");
  await expect(page.locator("html")).toHaveCSS(
    "background-color",
    "rgb(13, 26, 28)",
  );
});

test("reading typography and method marks use local fonts with no third-party requests", async ({
  page,
}, info) => {
  const external: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== "http://127.0.0.1:4173")
      external.push(request.url());
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await workspace(page);
  await page.getByLabel("Research question").fill("Synthetic query");
  await page
    .getByRole("button", { name: "Search collection", exact: true })
    .click();
  await expect(page.locator(".passage-card")).toHaveCount(2);
  await page.evaluate(() => document.fonts.ready);
  const excerpt = page.locator(".passage-text > p").first();
  await expect(excerpt).toHaveCSS("font-size", "18px");
  await expect(excerpt).toHaveCSS("line-height", "29.7px");
  await expect(excerpt).toHaveCSS("text-wrap-mode", "wrap");
  expect(
    await page
      .locator("kbd")
      .first()
      .evaluate((node) => getComputedStyle(node).fontFamily),
  ).toContain("Geist Variable");
  const fonts = await page.evaluate(() =>
    [...document.fonts]
      .filter((font) => font.status === "loaded")
      .map((font) => font.family),
  );
  for (const family of [
    "Newsreader Variable",
    "Geist Variable",
    "Geist Mono Variable",
  ])
    expect(fonts).toContain(family);
  expect(
    await page
      .locator(".metric")
      .first()
      .evaluate((node) => getComputedStyle(node).fontVariantNumeric),
  ).toBe("tabular-nums");
  for (const [method, color] of [
    ["sparse", "rgb(11, 107, 106)"],
    ["dense", "rgb(122, 62, 157)"],
  ]) {
    await expect(
      page.locator(`[data-retrieval="${method}"]`).first(),
    ).toHaveCSS("background-color", color);
  }
  const split = await page
    .locator('[data-method="hybrid"] .retrieval-mark')
    .first()
    .evaluate((node) => getComputedStyle(node).backgroundImage);
  expect(split).toContain("rgb(11, 107, 106) 50%");
  expect(split).toContain("rgb(122, 62, 157) 50%");
  const inspectorHit = page.locator(".passage-select").first();
  await inspectorHit.click();
  await expect(page.locator(".inspector blockquote")).toHaveCSS(
    "font-size",
    "18px",
  );
  await page.getByRole("button", { name: "Close evidence inspector" }).click();
  for (const theme of ["light", "dark"]) {
    await page.getByLabel("Appearance").selectOption(theme);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: info.outputPath(`reading-room-${theme}.png`),
      fullPage: true,
    });
  }
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  await expect(page.locator(".passage-card")).toHaveCount(2);
  await expect(page.locator(".passage-select").first()).toHaveText(
    "Synthetic paper b",
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("radio", { name: "Sparse", exact: true }).check();
  await expect(page.locator(".passage-select").first()).toHaveText(
    "Synthetic paper a",
  );
  expect(
    await page
      .locator(".passage-list")
      .evaluate((node) => node.getAnimations({ subtree: true }).length),
  ).toBe(0);
  expect(external).toEqual([]);
});

test("welcome theme control reflows on mobile", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/me", (route) =>
    route.fulfill({ status: 401, json: { code: "unauthenticated" } }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "A reading room for traceable evidence.",
    }),
  ).toBeVisible();
  await page.getByLabel("Appearance").selectOption("dark");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: info.outputPath("welcome-mobile-dark.png"),
    fullPage: true,
  });
});
