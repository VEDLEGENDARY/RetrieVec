import { test, expect } from "@playwright/test";

test("saved research opens directly and citations share the evidence pane", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const evidence = {
    evidence_id: "e1",
    citation_id: "citation",
    title: "A paper",
    text: "An exact retained passage.",
    page_range: [2, 2],
    source_id: null,
    snapshot_id: "snapshot",
  };
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
            original_question: "What is supported?",
            state: "completed",
            created_at: "2026-09-29T12:00:00Z",
          },
        ],
        next_cursor: null,
      };
    if (path === "/api/v1/runs/run")
      json = {
        run_id: "run",
        conversation_id: "conversation",
        original_question: "What is supported?",
        effective_query: "What is supported?",
        snapshot_id: "snapshot",
        state: "completed",
        configuration: {
          provider: "local",
          retrieval: "hybrid",
          generation: { model: "fixture", revision: "fixture-v1" },
        },
        result: {
          elapsed_ms: 10,
          evidence: [evidence],
          budget: { input_tokens: 20, excluded: [] },
          answer: {
            status: "answered",
            claims: [
              { id: "claim", text: "A supported claim.", evidence_ids: ["e1"] },
            ],
            comparisons: [],
            limitations: [],
          },
        },
      };
    if (path === "/api/v1/citations/citation") json = evidence;
    return route.fulfill({ json });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Saved research", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "All saved research" })
    .getByRole("button", { name: /What is supported/ })
    .click();
  await expect(page.getByText("A supported claim.")).toBeVisible();
  const citation = page
    .getByRole("button", { name: "Inspect citation e1", exact: true })
    .last();
  await citation.focus();
  await expect(
    page.getByRole("tooltip").filter({ hasText: "An exact retained passage." }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toBeHidden();
  await citation.click();
  const pane = page.getByRole("complementary", { name: "Evidence inspector" });
  await expect(pane).toBeFocused();
  await pane.getByRole("button", { name: "Copy with citation" }).click();
  await expect(pane.getByRole("status")).toHaveText(
    "Passage and citation copied.",
  );
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "Snapshot: snapshot",
  );
  await page.keyboard.press("Escape");
  await expect(citation).toBeFocused();
});
