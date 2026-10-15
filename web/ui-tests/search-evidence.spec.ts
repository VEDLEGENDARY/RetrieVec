import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile } from "node:fs/promises";
import { evidenceWorkbench } from "./fixtures/evidence-workbench";

test("method radios reorder shared cards, fetch a missing ranking once, and respect reduced motion", async ({
  page,
}) => {
  const fixture = await evidenceWorkbench(page, { onlyRequested: true });
  await page.goto("/");
  await page.getByLabel("Research question").fill("Sparse retrieval");
  await page.getByLabel("Research question").press("Enter");
  const cards = page.locator(".passage-card[data-passage]");
  await expect(cards.first()).toHaveAttribute("data-passage", "passage-b");
  await expect(cards.first().locator("mark").first()).toHaveText("Sparse");
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  await expect(cards.first()).toHaveAttribute("data-passage", "passage-c");
  await expect(cards.locator("mark")).toHaveCount(0);
  await page.getByRole("radio", { name: "Sparse", exact: true }).check();
  await expect(cards.first()).toHaveAttribute("data-passage", "passage-a");
  expect(fixture.requests).toHaveLength(3);
  await page.getByRole("radio", { name: "Hybrid", exact: true }).check();
  await expect(cards.first()).toHaveAttribute("data-passage", "passage-b");
  expect(fixture.requests).toHaveLength(3);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  expect(
    await page
      .locator(".passage-list")
      .evaluate((node) => node.getAnimations({ subtree: true }).length),
  ).toBe(0);
  expect(fixture.requests).toHaveLength(3);
  await page.getByLabel("Filter returned passages").fill("paper a");
  await expect(cards).toHaveCount(1);
  expect(fixture.requests).toHaveLength(3);
});

test("shortlist caps at six, compares ranks and snapshots, exports JSON and returns focus", async ({
  page,
}) => {
  await evidenceWorkbench(page);
  await page.goto("/");
  await page.getByLabel("Research question").fill("Original research question");
  await page
    .getByRole("button", { name: "Search collection", exact: true })
    .click();
  const actions = page.getByRole("button", {
    name: "Shortlist passage",
    exact: true,
  });
  for (let index = 0; index < 7; index++) await actions.nth(index).click();
  await expect(page.locator(".count-pill")).toHaveText("6/6");
  await expect(
    page.getByText("Your shortlist has six passages.", { exact: false }),
  ).toBeVisible();
  const chip = page.getByRole("button", { name: "Shortlist 6/6", exact: true });
  await chip.focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog", {
    name: "Compare shortlisted passages",
  });
  await expect(drawer).toBeVisible();
  await expect(drawer.locator(".comparison-passage")).toHaveCount(6);
  await expect(drawer.locator(".comparison-ranks").first()).toContainText(
    "Rank",
  );
  await expect(drawer.locator(".comparison-provenance").first()).toContainText(
    "snapshot-one",
  );
  const download = page.waitForEvent("download");
  await drawer
    .getByRole("button", { name: "Export shortlist", exact: true })
    .click();
  const output = JSON.parse(
    await readFile((await (await download).path())!, "utf8"),
  );
  expect(output.collection_id).toBe("one");
  expect(output.passages).toHaveLength(6);
  for (const item of output.passages) {
    expect(item.query).toBe("Original research question");
    expect(item.snapshot_id).toBe("snapshot-one");
    expect(item.hit.text).toBeTruthy();
    expect(item.methods).toEqual(["sparse", "dense", "hybrid"]);
    expect(item.ranks.hybrid.rank).toBeGreaterThan(0);
  }
  await page.keyboard.press("Escape");
  await expect(chip).toBeFocused();
  await actions.first().click();
  await actions.nth(6).click();
  await expect(page.locator(".count-pill")).toHaveText("6/6");
});

test("recent searches retain only five, support arrow/Home/End/Enter/Escape, and clear with collection scope", async ({
  page,
}) => {
  const fixture = await evidenceWorkbench(page);
  await page.goto("/");
  for (let index = 1; index <= 6; index++) {
    await page.getByLabel("Research question").fill(`Question ${index}`);
    await page.getByLabel("Research question").press("Enter");
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: `Results for “Question ${index}”` }),
    ).toBeVisible();
  }
  const recent = page.getByRole("button", {
    name: "Recent searches",
    exact: true,
  });
  await recent.focus();
  await page.keyboard.press("ArrowDown");
  const menu = page.getByRole("menu", { name: "Recent searches" });
  await expect(menu.getByRole("menuitem")).toHaveCount(5);
  await expect(menu.getByRole("menuitem").first()).toBeFocused();
  await page.keyboard.press("End");
  await expect(menu.getByRole("menuitem").last()).toBeFocused();
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Research question")).toHaveValue("Question 5");
  await expect(page.getByLabel("Research question")).toBeFocused();
  expect(fixture.requests).toHaveLength(6);
  await recent.click();
  await page.keyboard.press("Escape");
  await expect(recent).toBeFocused();
  await page
    .getByRole("navigation", { name: "Collections", exact: true })
    .getByRole("button", { name: /Evidence collection two/ })
    .click();
  await expect(page.locator(".count-pill")).toHaveText("0/6");
  await expect(recent).toBeDisabled();
  await page.reload();
  await expect(recent).toBeDisabled();
});

test("initial and partial method failures have working retry without losing available evidence", async ({
  page,
}) => {
  const fixture = await evidenceWorkbench(page, { onlyRequested: true });
  fixture.setFailAll(true);
  await page.goto("/");
  await page.getByLabel("Research question").fill("Retry the finding");
  await page.getByLabel("Research question").press("Enter");
  await expect(page.getByRole("alert")).toContainText("Search failed");
  fixture.setFailAll(false);
  await page.getByRole("button", { name: "Retry search" }).click();
  await expect(page.locator(".passage-card[data-passage]")).toHaveCount(7);
  fixture.failures.add("dense");
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  await expect(page.getByRole("alert")).toContainText(
    "Available Hybrid results remain",
  );
  await expect(page.locator(".passage-card[data-passage]")).toHaveCount(7);
  fixture.failures.clear();
  await page.getByRole("button", { name: "Retry search" }).click();
  await expect(
    page.locator(".passage-card[data-passage]").first(),
  ).toHaveAttribute("data-passage", "passage-c");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("untrusted passages render as text; copying and the Atlas slot retain actual identities", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await evidenceWorkbench(page);
  await page.goto("/");
  await page.getByLabel("Research question").fill("Retrieval script");
  await page.getByLabel("Research question").press("Enter");
  await page.getByLabel("Filter returned passages").fill("paper g");
  const card = page.locator(".passage-card[data-passage]");
  await expect(card.locator(".passage-text")).toContainText(
    '<img src=x onerror="window.injected=true">',
  );
  await expect(card.locator("img,script")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as Window & { injected?: boolean }).injected,
    ),
  ).toBeUndefined();
  await card
    .getByRole("button", { name: "Copy citation", exact: true })
    .click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "Snapshot: snapshot-one",
  );
  await card
    .getByRole("button", { name: "Synthetic paper g", exact: true })
    .click();
  await expect(page.locator(".atlas-placeholder")).toHaveAttribute(
    "data-selected-passage",
    "passage-g",
  );
  await page.keyboard.press("Escape");
  await page.getByText("Evidence Atlas", { exact: true }).click();
  await expect(
    page.getByText("Atlas arrives in task 04", { exact: true }),
  ).toBeVisible();
});

for (const width of [1280, 390])
  test(`loading skeletons match cards without layout shift and both search themes pass axe at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await evidenceWorkbench(page, { gate });
    await page.goto("/");
    await page.evaluate(() => document.fonts.ready);
    await page.getByLabel("Research question").fill("Sparse retrieval");
    await page.getByLabel("Research question").press("Enter");
    const skeleton = page.locator(".passage-skeleton").first();
    await expect(skeleton).toBeVisible();
    const before = await skeleton.boundingBox();
    await page.evaluate(() => {
      (
        window as Window & { testShift?: number; testShifts?: unknown[] }
      ).testShift = 0;
      (window as Window & { testShifts?: unknown[] }).testShifts = [];
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as (PerformanceEntry & {
          hadRecentInput: boolean;
          value: number;
          sources: {
            node?: Element;
            previousRect: DOMRectReadOnly;
            currentRect: DOMRectReadOnly;
          }[];
        })[])
          if (!entry.hadRecentInput) {
            (window as Window & { testShift: number }).testShift += entry.value;
            (window as Window & { testShifts: unknown[] }).testShifts.push({
              value: entry.value,
              sources: entry.sources.map((source) => ({
                html: source.node?.outerHTML.slice(0, 350),
                before: source.previousRect,
                after: source.currentRect,
              })),
            });
          }
      }).observe({ type: "layout-shift", buffered: false });
    });
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    release();
    await expect(page.locator(".passage-card[data-passage]")).toHaveCount(7);
    const after = await page
      .locator(".passage-card[data-passage]")
      .first()
      .boundingBox();
    expect(after?.height).toBe(before?.height);
    expect(after?.y).toBe(before?.y);
    await page.evaluate(
      () =>
        new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        ),
    );
    await info.attach("loading-layout-shifts", {
      body: JSON.stringify(
        await page.evaluate(
          () => (window as Window & { testShifts: unknown[] }).testShifts,
        ),
      ),
      contentType: "application/json",
    });
    expect(
      await page.evaluate(
        () => (window as Window & { testShift: number }).testShift,
      ),
    ).toBe(0);
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
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({
        path: info.outputPath(`search-evidence-${theme}.png`),
        fullPage: true,
      });
      if (width === 1280) {
        await page
          .locator(".passage-card[data-passage]")
          .first()
          .scrollIntoViewIfNeeded();
        await page.screenshot({
          path: info.outputPath(`reading-view-${theme}.png`),
        });
      }
    }
  });

test("passage actions, comparison focus containment and mobile scroll snap work from the keyboard", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await evidenceWorkbench(context);
  await page.goto("/");
  const question = page.getByLabel("Research question");
  await question.fill("Keyboard evidence");
  await question.press("Tab");
  await expect(
    page.getByRole("radio", { name: "Hybrid", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(
    page.getByRole("radio", { name: "Dense", exact: true }),
  ).toBeChecked();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Search collection", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  const first = page.locator(".passage-card[data-passage]").first();
  const title = first.locator(".passage-select");
  await title.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(title).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(first.locator(".passage-text")).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  await expect(
    first.getByRole("button", { name: "Shortlist passage" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Tab");
  const popup = page.waitForEvent("popup");
  await page.keyboard.press("Enter");
  const source = await popup;
  expect(source.url()).toContain("snapshot_id=snapshot-one#page=1");
  await source.close();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "Question: Keyboard evidence",
  );
  await page.getByRole("button", { name: "Shortlist passage" }).nth(1).focus();
  await page.keyboard.press("Space");
  await page.locator("#passage-shortlist").focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog", {
    name: "Compare shortlisted passages",
  });
  for (let index = 0; index < 20; index++) {
    await page.keyboard.press("Tab");
    expect(
      await drawer.evaluate((node) => node.contains(document.activeElement)),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(drawer.locator(".comparison-passages")).toHaveCSS(
    "scroll-snap-type",
    "x mandatory",
  );
  await drawer.locator(".comparison-passages").focus();
  await page.keyboard.press("End");
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.keyboard.press("Escape");
  await expect(page.locator("#passage-shortlist")).toBeFocused();
});

test("switching during initial and replacement requests keeps the pending question and newest method", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const fixture = await evidenceWorkbench(page, { onlyRequested: true, gate });
  await page.goto("/");
  await page.getByLabel("Research question").fill("First question");
  await page.getByLabel("Research question").press("Enter");
  await expect.poll(() => fixture.requests.length).toBe(1);
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  await expect.poll(() => fixture.requests.length).toBe(2);
  release();
  const first = page.locator(".passage-card[data-passage]").first();
  await expect(first).toHaveAttribute("data-method", "dense");
  await expect(first).toHaveAttribute("data-passage", "passage-c");
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  const next: { query: string; retrieval: string; snapshot_id: string }[] = [];
  await page.route("**/api/v1/search", async (route) => {
    next.push(route.request().postDataJSON());
    await pending;
    await route.fallback();
  });
  await page.getByLabel("Research question").fill("Replacement question");
  await page.getByLabel("Research question").press("Enter");
  await expect.poll(() => next.length).toBe(1);
  await page.getByRole("radio", { name: "Sparse", exact: true }).check();
  await expect.poll(() => next.length).toBe(2);
  expect(next.map((request) => request.query)).toEqual([
    "Replacement question",
    "Replacement question",
  ]);
  expect(next.every((request) => request.snapshot_id === "snapshot-one")).toBe(
    true,
  );
  finish();
  await expect(first).toHaveAttribute("data-method", "sparse");
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Results for “Replacement question”" }),
  ).toBeVisible();
});

test("explicit cached method filters show their own ranks and shortlist export quick action remains reachable", async ({
  page,
}) => {
  const fixture = await evidenceWorkbench(page);
  await page.goto("/");
  await page.getByLabel("Research question").fill("Compare methods");
  await page.getByLabel("Research question").press("Enter");
  await page.getByLabel("Show retrieval method").selectOption("dense");
  const region = page.getByRole("region", { name: "Dense · Cosine" });
  await expect(region.locator(".passage-card").first()).toHaveAttribute(
    "data-passage",
    "passage-c",
  );
  await expect(region.locator(".passage-card").first()).toHaveAttribute(
    "data-method",
    "dense",
  );
  expect(fixture.requests).toHaveLength(1);
  await region
    .getByRole("button", { name: "Shortlist passage" })
    .first()
    .click();
  await page.getByRole("button", { name: /Quick actions/ }).click();
  await page
    .getByRole("combobox", { name: "Find actions and collections" })
    .fill("Export evidence shortlist");
  await page
    .getByRole("option", { name: /^Export evidence shortlist / })
    .click();
  await expect(page.locator("#export-shortlist")).toBeFocused();
  const download = page.waitForEvent("download");
  await page.keyboard.press("Enter");
  const result = JSON.parse(
    await readFile((await (await download).path())!, "utf8"),
  );
  expect(result.passages[0].hit.chunk_id).toBe("passage-c");
});

test("partial comparison names missing methods and rejects a response from another snapshot", async ({
  page,
}) => {
  await evidenceWorkbench(page, { onlyRequested: true });
  let partial = true;
  let mismatch = false;
  const requested: { snapshot_id: string }[] = [];
  await page.route("**/api/v1/search", async (route) => {
    const body = route.request().postDataJSON();
    requested.push(body);
    if (partial || mismatch)
      return route.fulfill({
        json: {
          collection_id: "one",
          snapshot_id: mismatch ? "different-snapshot" : body.snapshot_id,
          query: body.query,
          mode: body.mode,
          results: {
            hybrid: { hits: [], configuration: {}, total_matches: 0 },
          },
        },
      });
    return route.fallback();
  });
  await page.goto("/");
  await page.getByLabel("Research question").fill("Pinned evidence");
  await page.getByText("More search options", { exact: true }).click();
  await page
    .getByRole("button", { name: "Compare methods", exact: true })
    .click();
  await page.getByLabel("Research question").press("Enter");
  await expect(page.getByRole("alert")).toContainText(
    "Sparse, Dense results were unavailable",
  );
  partial = false;
  await page.getByRole("button", { name: "Retry search" }).click();
  await expect(page.locator(".passage-card[data-passage]")).toHaveCount(7);
  mismatch = true;
  // A different query has no cached rankings to hide the identity mismatch.
  await page.getByLabel("Research question").fill("Another pinned question");
  await page.getByLabel("Research question").press("Enter");
  await expect(page.getByRole("alert")).toContainText("different snapshot");
  await expect(page.locator(".passage-card[data-passage]")).toHaveCount(7);
  expect(requested.every((body) => body.snapshot_id === "snapshot-one")).toBe(
    true,
  );
});

for (const status of [403, 404])
  test(`unavailable collection responses clear private evidence and undo state (${status})`, async ({
    page,
  }) => {
    await evidenceWorkbench(page);
    await page.goto("/");
    await page
      .getByLabel("Research question")
      .fill("Private evidence question");
    await page.getByLabel("Research question").press("Enter");
    const actions = page.getByRole("button", {
      name: "Shortlist passage",
      exact: true,
    });
    await actions.first().click();
    await actions.nth(1).click();
    await actions.first().click();
    await expect(
      page.getByRole("button", { name: "Undo remove passage" }),
    ).toBeVisible();
    let denied = true;
    let pending: Promise<void> | null = null;
    let started = false;
    await page.route("**/api/v1/search", async (route) => {
      if (denied)
        return route.fulfill({
          status,
          json: { code: "unavailable", message: "Collection unavailable." },
        });
      started = true;
      await pending;
      return route.fallback();
    });
    await page.getByLabel("Research question").fill("Another private question");
    await page.getByLabel("Research question").press("Enter");
    await expect(page.locator(".passage-card[data-passage]")).toHaveCount(0);
    if (status === 404) {
      await expect(
        page.getByRole("heading", { name: "Start with a collection" }),
      ).toBeVisible();
      await expect(page.locator("#passage-shortlist")).toHaveCount(0);
      return;
    }
    await expect(page.locator(".count-pill")).toHaveText("0/6");
    await expect(page.locator("#recent-searches")).toBeDisabled();
    denied = false;
    let release!: () => void;
    pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.getByLabel("Research question").press("Enter");
    await expect.poll(() => started).toBe(true);
    await page
      .getByRole("button", { name: "Cancel search", exact: true })
      .click();
    release();
    await expect(
      page.getByRole("button", { name: "Undo remove passage" }),
    ).toHaveCount(0);
    await expect(page.locator(".count-pill")).toHaveText("0/6");
  });
