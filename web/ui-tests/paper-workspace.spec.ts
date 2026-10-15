import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const collection = {
  collection_id: "papers",
  title: "My literature review",
  visibility: "private",
  can_manage: true,
  active_snapshot: "snapshot",
};
const paper = {
  source_id: "source-one",
  display_name: "Methods study.pdf",
  media_type: "application/pdf",
  size_bytes: 4096,
  created_at: "2026-10-14T12:00:00Z",
  state: "succeeded",
};
async function workspace(page: Page, empty = false) {
  let created = false;
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url()),
      path = url.pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "reader", csrf_token: "csrf" };
    else if (path === "/api/v1/collections") {
      if (route.request().method() === "POST") {
        created = true;
        return route.fulfill({
          status: 201,
          json: { ...collection, active_snapshot: null },
        });
      }
      json =
        empty && !created
          ? []
          : [
              {
                ...collection,
                active_snapshot: created ? null : collection.active_snapshot,
              },
            ];
    } else if (path.endsWith("/papers")) {
      const query = url.searchParams.get("q") ?? "",
        after = url.searchParams.get("after");
      json = {
        items:
          query === "missing" || created
            ? []
            : after
              ? [
                  {
                    ...paper,
                    source_id: "source-two",
                    display_name: "Findings study.pdf",
                    state: "failed",
                  },
                ]
              : [paper],
        next_cursor:
          query === "missing" || created || after ? null : "next-page",
      };
    } else if (path.endsWith("/runs")) json = { items: [], next_cursor: null };
    return route.fulfill({ json });
  });
  await page.goto("/");
}

test("creating a collection opens uploads and preserves the collection in the route", async ({
  page,
}) => {
  await workspace(page, true);
  await page
    .getByLabel("New collection", { exact: true })
    .fill(collection.title);
  await page
    .locator(".new-collection")
    .getByRole("button", { name: "Create collection" })
    .click();
  await expect(page).toHaveURL(/view=sources&collection=papers/);
  await expect(
    page.getByRole("heading", { name: "Add to your sources" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Research workflow" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Choose documents", { exact: true }),
  ).toBeVisible();
});

test("question starters only populate the composer and focus it", async ({
  page,
}) => {
  let submitted = false;
  await workspace(page);
  page.on("request", (request) => {
    if (request.url().endsWith("/search")) submitted = true;
  });
  await page.getByText("Question suggestions", { exact: true }).click();
  await page
    .getByRole("button", {
      name: "What limitations do the authors report?",
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Research question")).toHaveValue(
    "What limitations do the authors report?",
  );
  await expect(page.getByLabel("Research question")).toBeFocused();
  expect(submitted).toBe(false);
});

test("paper library filters, paginates, opens original links and distinguishes failed uploads", async ({
  page,
}) => {
  await workspace(page);
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: paper.display_name }),
  ).toBeVisible();
  const original = page.getByRole("link", { name: /Open original Methods/ });
  await expect(original).toHaveAttribute(
    "href",
    "/api/v1/sources/source-one?snapshot_id=snapshot",
  );
  await expect(original).toHaveAttribute("target", "_blank");
  await page.getByRole("button", { name: "Next papers" }).click();
  await expect(
    page.getByRole("heading", { name: "Findings study.pdf" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Open original/ })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "Next papers" }),
  ).toBeDisabled();
  await page.getByLabel("Find an uploaded paper").fill("missing");
  await expect(
    page.getByRole("heading", { name: "No matching papers" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear paper search" }).click();
  await expect(
    page.getByRole("heading", { name: paper.display_name }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("paper library recovers from a malformed response with an explicit retry", async ({
  page,
}) => {
  await workspace(page);
  await page.route("**/papers?*", (route) =>
    route.fulfill({
      json: { items: [{ ...paper, created_at: "invalid" }], next_cursor: null },
    }),
  );
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Retry loading papers" }),
  ).toBeVisible();
  await page.route("**/papers?*", (route) =>
    route.fulfill({ json: { items: [paper], next_cursor: null } }),
  );
  await page.getByRole("button", { name: "Retry loading papers" }).click();
  await expect(
    page.getByRole("heading", { name: paper.display_name }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("research guide returns keyboard focus and new paper layouts pass automated accessibility checks", async ({
  page,
}, info) => {
  await workspace(page);
  const trigger = page.getByRole("button", {
    name: "Research guide",
    exact: true,
  });
  await trigger.click();
  const guide = page.getByRole("dialog", {
    name: "A paper to evidence workflow",
  });
  await expect(guide).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: paper.display_name }),
  ).toBeVisible();
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 960 });
      if (width === 390)
        await page.getByRole("button", { name: "Open navigation" }).click();
      await trigger.click();
      await expect(guide).toBeVisible();
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze()
        ).violations,
      ).toEqual([]);
      await page.screenshot({
        path: info.outputPath(`guide-${scheme}-${width}.png`),
        fullPage: true,
      });
      await page.keyboard.press("Escape");
      if (width === 390) await page.keyboard.press("Escape");
      await page.evaluate(() =>
        window.scrollTo({ top: 0, behavior: "instant" }),
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze()
        ).violations,
      ).toEqual([]);
      await page.screenshot({
        path: info.outputPath(`paper-library-${scheme}-${width}.png`),
        fullPage: true,
      });
    }
  }
});
