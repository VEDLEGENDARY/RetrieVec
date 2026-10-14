import { test, expect } from "@playwright/test";

test("archive can be undone without a confirmation dialog", async ({
  page,
}) => {
  const collection = {
    collection_id: "demo",
    title: "My papers",
    visibility: "private",
    can_manage: true,
    active_snapshot: null,
  };
  let archived = false;
  let restored = false;
  page.on("dialog", () => {
    throw new Error("Archive should offer Undo");
  });
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/papers"))
      return route.fulfill({
        json: { items: [], next_cursor: null },
      });
    if (route.request().method() === "DELETE") {
      archived = true;
      return route.fulfill({ status: 204 });
    }
    if (path.endsWith("/restore")) {
      expect(route.request().headers()["x-csrf-token"]).toBe("test");
      archived = false;
      restored = true;
      return route.fulfill({ json: collection });
    }
    return route.fulfill({
      json: path.endsWith("/me")
        ? { principal_id: "demo", csrf_token: "test" }
        : path === "/api/v1/collections"
          ? archived
            ? []
            : [collection]
          : [],
    });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Archive collection", exact: true })
    .click();
  await expect(
    page.getByText("cancelled processing stays cancelled", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Undo archive" }).click();
  await expect(
    page.getByRole("heading", { name: "My papers", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Undo archive" })).toHaveCount(
    0,
  );
  expect(restored).toBe(true);
});
