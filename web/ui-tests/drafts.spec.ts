import { test, expect } from "@playwright/test";

test("question drafts survive reload, follow Ask modes, and clear on logout", async ({
  page,
}) => {
  page.on("pageerror", (error) => {
    throw error;
  });
  let signedIn = true;
  await page.route("**/auth/logout", (route) => {
    signedIn = false;
    return route.fulfill({ status: 204 });
  });
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/me"))
      return route.fulfill({
        status: signedIn ? 200 : 401,
        json: signedIn ? { principal_id: "owner", csrf_token: "token" } : {},
      });
    return route.fulfill({
      json:
        path === "/api/v1/collections"
          ? [
              {
                collection_id: "one",
                title: "Papers",
                visibility: "private",
                can_manage: true,
                active_snapshot: "snapshot",
              },
            ]
          : [],
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Papers", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Research question").fill("Draft to restore");
  await page.getByRole("button", { name: "Answer", exact: true }).click();
  await expect(page.getByLabel("Question for cited answer")).toHaveValue(
    "Draft to restore",
  );
  await page.reload();
  await expect(page.getByLabel("Research question")).toHaveValue(
    "Draft to restore",
  );
  await page.evaluate(() => {
    localStorage.setItem(
      "retrievec:draft:v1:owner:one:question",
      JSON.stringify({ text: "Expired secret", expires: Date.now() - 1 }),
    );
    localStorage.setItem(
      "retrievec:draft:v1:another:one:question",
      JSON.stringify({ text: "Other principal", expires: Date.now() + 100000 }),
    );
    localStorage.setItem(
      "retrievec:draft:v1:owner:two:question",
      JSON.stringify({
        text: "Other collection",
        expires: Date.now() + 100000,
      }),
    );
  });
  await page.reload();
  await expect(page.getByLabel("Research question")).toHaveValue("");
  expect(
    await page.evaluate(() =>
      localStorage.getItem("retrievec:draft:v1:another:one:question"),
    ),
  ).toBeNull();
  expect(
    await page.evaluate(() =>
      localStorage.getItem("retrievec:draft:v1:owner:two:question"),
    ),
  ).toContain("Other collection");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Sign in to your workspace/ }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).filter((key) =>
        key.startsWith("retrievec:draft:"),
      ),
    ),
  ).toEqual([]);
});
