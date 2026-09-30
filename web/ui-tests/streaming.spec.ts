import { test, expect } from "@playwright/test";

test("early evidence and provisional deltas disappear when run access changes", async ({
  page,
}) => {
  let revoked = false;
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "owner", csrf_token: "token" };
    if (path === "/api/v1/collections")
      json = [
        {
          collection_id: "one",
          title: "Papers",
          visibility: "private",
          active_snapshot: "snapshot",
          can_manage: true,
        },
      ];
    if (path === "/api/v1/collections/one/runs")
      json = {
        items: [
          {
            run_id: "run",
            conversation_id: "conversation",
            original_question: "Question",
            state: "generating",
            created_at: "2026-09-29T12:00:00Z",
          },
        ],
        next_cursor: null,
      };
    if (path === "/api/v1/runs/run") {
      if (revoked)
        return route.fulfill({
          status: 404,
          json: { code: "unavailable", message: "Access changed." },
        });
      json = {
        run_id: "run",
        conversation_id: "conversation",
        original_question: "Question",
        effective_query: "Question",
        snapshot_id: "snapshot",
        state: "generating",
        configuration: {
          provider: "local",
          retrieval: "hybrid",
          generation: { model: "fixture", revision: "fixture" },
        },
        result: null,
      };
    }
    if (path === "/api/v1/runs/run/events")
      return route.fulfill({
        contentType: "text/event-stream",
        body: `retry: 1500\nid: 1\nevent: evidence_ready\ndata: ${JSON.stringify({ run_id: "run", evidence: [{ evidence_id: "e1", title: "Early source", text: "Retrieved before completion.", page_range: [1, 1] }] })}\n\nid: 2\nevent: draft_delta\ndata: ${JSON.stringify({ run_id: "run", text: "provisional fragment" })}\n\n`,
      });
    return route.fulfill({ json });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Saved research", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "All saved research" })
    .getByRole("button", { name: /Question/ })
    .click();
  await expect(page.getByText("Retrieved before completion.")).toBeVisible();
  await page.getByText("Live draft — not yet checked", { exact: true }).click();
  await expect(
    page.getByText("provisional fragment", { exact: true }),
  ).toBeVisible();
  revoked = true;
  await expect(page.getByText("Access changed.")).toBeVisible();
  await expect(page.getByText("Retrieved before completion.")).toHaveCount(0);
  await expect(
    page.getByText("provisional fragment", { exact: true }),
  ).toHaveCount(0);
});
