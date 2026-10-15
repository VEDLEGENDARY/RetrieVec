import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function workspace(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: path.endsWith("/me")
        ? { principal_id: "polish", csrf_token: "test" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "papers",
                title: "Evidence library",
                active_snapshot: "snapshot",
                visibility: "private",
                can_manage: true,
              },
            ]
          : [],
    });
  });
  await page.goto("/");
  await expect(page.getByLabel("Research question")).toBeVisible();
}

test("reranking is explicit, resets across methods, and explains fallback", async ({
  page,
}) => {
  await workspace(page);
  const submit = page.getByRole("button", { name: /Search collection/ });
  await expect(submit).toBeDisabled();
  await page.getByLabel("Research question").fill("Compare the methods");
  await page.getByText("More search options", { exact: true }).click();
  const rerank = page.getByRole("checkbox", { name: "Experimental reranking" });
  await expect(rerank).not.toBeChecked();
  await rerank.check();
  await page.getByRole("radio", { name: "Dense", exact: true }).check();
  await expect(rerank).not.toBeChecked();
  await expect(rerank).toBeDisabled();
  await page.getByRole("radio", { name: "Hybrid", exact: true }).check();
  await rerank.check();
  await page.route("**/api/v1/search", (route) => {
    expect(route.request().postDataJSON().rerank).toBe(true);
    expect(route.request().postDataJSON().section).toBe("methods");
    return route.fulfill({
      json: {
        collection_id: "papers",
        snapshot_id: "snapshot",
        query: "Compare the methods",
        results: {
          hybrid: {
            hits: [],
            total_matches: 0,
            configuration: {},
            reranker: { status: "fallback" },
          },
        },
      },
    });
  });
  await page.getByText("More section filters", { exact: true }).click();
  await page
    .getByRole("region", { name: "Ask your sources" })
    .getByLabel("Paper section", { exact: true })
    .selectOption("methods");
  await submit.click();
  await expect(
    page.getByRole("status").filter({ hasText: "original hybrid order" }),
  ).toBeVisible();
});

test("network failures and invalid JSON provide actionable messages", async ({
  page,
}) => {
  await workspace(page);
  await page.getByLabel("New collection").fill("New papers");
  await page.route("**/api/v1/collections", (route) =>
    route.abort("internetdisconnected"),
  );
  await page
    .getByRole("button", { name: "Create collection", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Check your connection");
  await page.route("**/api/v1/collections", (route) =>
    route.fulfill({ body: "incomplete", contentType: "text/plain" }),
  );
  await page
    .getByRole("button", { name: "Create collection", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("incomplete response");
});

test("welcome is readable and accessible on desktop, mobile, light and dark", async ({
  page,
}) => {
  await page.route("**/api/v1/me", (route) =>
    route.fulfill({ status: 401, json: { code: "unauthorized" } }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Sign in to your workspace" }),
  ).toBeVisible();
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 960 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const scan = await new AxeBuilder({ page }).analyze();
      expect(
        scan.violations.filter((v) =>
          ["serious", "critical"].includes(v.impact ?? ""),
        ),
      ).toEqual([]);
      await page.screenshot({
        path: `test-results/welcome-${scheme}-${width}.png`,
        fullPage: true,
      });
    }
  }
});
