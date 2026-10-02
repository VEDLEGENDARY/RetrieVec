import { test, expect, type Page } from "@playwright/test";

async function workspace(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const json =
      path === "/api/v1/me"
        ? { principal_id: "fixture", csrf_token: "fixture-token" }
        : path === "/api/v1/collections"
          ? [
              {
                collection_id: "fixture",
                title: "Retrieval methods",
                visibility: "private",
                active_snapshot: null,
                can_manage: true,
              },
            ]
          : [];
    return route.fulfill({ json });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Retrieval methods", exact: true }),
  ).toBeVisible();
}

test("quick actions announce keyboard selection and reset on reopen", async ({
  page,
}) => {
  await workspace(page);
  const trigger = page.getByRole("button", { name: /Quick actions/ });
  await trigger.click();
  const input = page.getByRole("combobox", {
    name: "Find actions and collections",
  });
  await expect(input).toBeFocused();
  await input.fill("Sources");
  const sources = page.getByRole("option", { name: /Sources/ });
  await expect(sources).toHaveAttribute("aria-selected", "true");
  await expect(input).toHaveAttribute(
    "aria-activedescendant",
    (await sources.getAttribute("id"))!,
  );
  await input.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Add to your sources" }),
  ).toBeVisible();
  await trigger.click();
  await input.fill("nothing matches this");
  await expect(
    page.getByRole("status").filter({ hasText: "No matching actions" }),
  ).toBeVisible();
  await expect(input).not.toHaveAttribute("aria-activedescendant");
  await input.press("Escape");
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(input).toHaveValue("");
  await expect(input).toBeFocused();
});

test("mobile navigation confines focus, closes on Escape, and fits the viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await workspace(page);
  const trigger = page.getByRole("button", { name: "Open navigation" });
  await trigger.click();
  const navigation = page.getByRole("dialog", {
    name: "Collection navigation",
  });
  await expect(navigation).toBeVisible();
  const last = navigation.getByRole("button", { name: "Sign out" });
  await last.focus();
  await page.keyboard.press("Tab");
  await expect(
    navigation.getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(navigation).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("malformed API errors provide a recoverable message", async ({ page }) => {
  await workspace(page);
  await page.route("**/api/v1/collections", (route) =>
    route.fulfill({ status: 503, json: null }),
  );
  await page.getByLabel("New collection").fill("New research");
  await page
    .getByRole("button", { name: "Create collection", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveText(
    "The request could not be completed. Try again shortly.",
  );
  await expect(
    page.getByRole("button", { name: "Create collection", exact: true }),
  ).toBeEnabled();
});

test("logout cancels collection refresh and discards private workspace state", async ({
  page,
}) => {
  await workspace(page);
  await page.route("**/auth/logout", (route) => route.fulfill({ status: 204 }));
  let notifyRefresh!: () => void;
  let releaseRefresh!: () => void;
  const started = new Promise<void>((resolve) => {
    notifyRefresh = resolve;
  });
  const release = new Promise<void>((resolve) => {
    releaseRefresh = resolve;
  });
  await page.route("**/api/v1/collections", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: { collection_id: "new", title: "New research" },
      });
    } else {
      notifyRefresh();
      await release;
      await route
        .fulfill({
          json: [
            { collection_id: "new", title: "New research", can_manage: true },
          ],
        })
        .catch(() => {});
    }
  });
  await page.getByLabel("New collection").fill("New research");
  await page
    .getByRole("button", { name: "Create collection", exact: true })
    .click();
  await started;
  const cancelled = page.waitForEvent(
    "requestfailed",
    (request) => new URL(request.url()).pathname === "/api/v1/collections",
  );
  await page.getByRole("button", { name: "Sign out" }).click();
  await cancelled;
  releaseRefresh();
  await expect(
    page.getByRole("link", { name: /Sign in to your workspace/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Retrieval methods", exact: true }),
  ).toHaveCount(0);
});
