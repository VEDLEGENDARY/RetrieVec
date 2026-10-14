import { test, expect, type Page } from "@playwright/test";
import { writeFile } from "node:fs/promises";

// Synthetic transport fixtures: these test UI behavior, not backend authorization.
const evidence = ["used", "candidate"].map((id) => ({
  evidence_id: id,
  citation_id: id,
  chunk_id: id,
  title: `${id} source`,
  text: `Synthetic ${id} passage`,
  page_range: [1, 1],
  source_id: null,
  snapshot_id: "snapshot",
}));
const run = {
  run_id: "run",
  conversation_id: "conversation",
  original_question: "Saved question",
  effective_query: "Saved question",
  snapshot_id: "snapshot",
  state: "completed",
  error_code: null,
  configuration: {
    provider: "local",
    retrieval: "hybrid",
    generation: { model: "Fixture model", revision: "fixture" },
  },
  result: {
    elapsed_ms: 0,
    evidence,
    budget: { input_tokens: 0, excluded: [] },
    answer: {
      status: "partial",
      claims: [
        { id: "claim", text: "Synthetic claim", evidence_ids: ["used"] },
      ],
      comparisons: [],
      limitations: [],
    },
  },
};
async function workspace(
  page: Page,
  provider: "local" | "cloud" | "none" = "local",
  providerGate?: Promise<void>,
) {
  const requests: { path: string; method: string; query: string }[] = [];
  let consented = provider === "local";
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url()),
      path = url.pathname;
    if (path.endsWith("/papers"))
      return route.fulfill({
        json: { items: [], next_cursor: null },
      });
    requests.push({
      path,
      method: route.request().method(),
      query: url.search,
    });
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "fixture", csrf_token: "fixture" };
    else if (path === "/api/v1/collections")
      json = ["one", "two"].map((id) => ({
        collection_id: id,
        title: `Collection ${id}`,
        visibility: "private",
        active_snapshot: "snapshot",
        can_manage: true,
      }));
    else if (path.endsWith("/consent")) {
      consented = route.request().method() === "PUT";
      return route.fulfill({ status: 204 });
    } else if (path.endsWith("/providers")) {
      if (path.includes("/one/")) await providerGate;
      json =
        provider === "none"
          ? []
          : [
              {
                name: provider,
                model: "Fixture model",
                cloud: provider === "cloud",
                consented,
              },
            ];
    } else if (/\/collections\/[^/]+\/runs$/.test(path))
      json = {
        items: [run],
        next_cursor: url.searchParams.has("before") ? null : "run",
      };
    else if (path === "/api/v1/runs/run") json = run;
    else if (
      path === "/api/v1/conversations" &&
      route.request().method() === "POST"
    )
      json = { conversation_id: "conversation", title: "Fixture" };
    else if (path === "/api/v1/conversations/conversation/runs")
      json = route.request().method() === "POST" ? run : [run];
    else if (path === "/api/v1/search")
      json = {
        collection_id: "one",
        snapshot_id: "snapshot",
        query: "Fixture",
        mode: "free_text",
        results: {
          hybrid: {
            hits: evidence.map((item, index) => ({
              ...item,
              rank: index + 1,
              bm25_score: 1,
              cosine_score: 0.5,
              rrf_score: 0.01,
            })),
            total_matches: 2,
            configuration: {},
          },
        },
      };
    return route.fulfill({ json });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Collection one", exact: true }),
  ).toBeVisible();
  return requests;
}
async function command(page: Page, label: string) {
  await page.getByRole("button", { name: /Quick actions/ }).click();
  await page
    .getByRole("combobox", { name: "Find actions and collections" })
    .fill(label);
  await page
    .getByRole("option", {
      name: new RegExp(
        "^" + label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " ",
      ),
    })
    .click();
}

test("configured consented provider defaults to Answer with collapsed model context", async ({
  page,
}) => {
  await workspace(page);
  await expect(
    page.getByRole("button", { name: "Answer", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".ask-mode-context")).toContainText(
    "Fixture model · Local",
  );
  await expect(page.getByLabel("Generation provider")).not.toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Workspace sections" })
      .getByRole("button"),
  ).toHaveText(["Ask", "Sources", "Saved research"]);
});

test("cloud consent is explicit and keyboard submission cannot bypass it", async ({
  page,
}) => {
  const requests = await workspace(page, "cloud");
  await expect(page.locator(".ask-mode-context")).toContainText(
    "Consent required",
  );
  await expect(
    page.getByRole("button", { name: "Find passages", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Answer", exact: true }).click();
  const question = page.getByLabel("Question for cited answer");
  await question.fill("Fixture question");
  await question.press("Control+Enter");
  await question.press("Meta+Enter");
  await expect(
    page.getByRole("button", { name: "Generate cited answer", exact: true }),
  ).toBeDisabled();
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  await page.getByRole("button", { name: "Allow this cloud provider" }).click();
  await expect(
    page.getByRole("button", { name: "Generate cited answer", exact: true }),
  ).toBeEnabled();
  expect(requests.filter((r) => r.method === "PUT").map((r) => r.path)).toEqual(
    ["/api/v1/collections/one/providers/cloud/consent"],
  );
});

test("late provider responses preserve explicit mode choice and are cancelled across collections", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await workspace(page, "local", gate);
  await page
    .getByRole("button", { name: "Find passages", exact: true })
    .click();
  release();
  await expect(page.locator(".ask-mode-context")).toContainText(
    "Fixture model · Local",
  );
  await expect(page.getByLabel("Research question")).toBeVisible();
  const secondGate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/collections/one/providers", async (route) => {
    await secondGate;
    await route
      .fulfill({
        json: [
          {
            name: "stale",
            model: "Stale model",
            cloud: true,
            consented: false,
          },
        ],
      })
      .catch(() => {});
  });
  await page.reload();
  const cancelled = page.waitForEvent("requestfailed", (request) =>
    request.url().endsWith("/collections/one/providers"),
  );
  await page.getByRole("button", { name: "Collection two Private" }).click();
  await cancelled;
  release();
  await expect(page.locator(".ask-mode-context")).toContainText(
    "Fixture model · Local",
  );
  await expect(page.locator(".ask-mode-context")).not.toContainText(
    "Stale model",
  );
  await expect(
    page.getByRole("button", { name: "Answer", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("unconfigured generation explains passage mode", async ({ page }) => {
  await workspace(page, "none");
  await expect(page.locator(".ask-mode-context")).toContainText(
    "No answer provider configured",
  );
  await expect(page.getByLabel("Research question")).toBeVisible();
});

for (const key of ["Control", "Meta"])
  test(`${key}+Enter submits both modes and ignores IME composition`, async ({
    page,
  }) => {
    const requests = await workspace(page);
    const answer = page.getByLabel("Question for cited answer");
    await answer.fill("Fixture question");
    await answer.dispatchEvent("keydown", {
      key: "Enter",
      ctrlKey: true,
      isComposing: true,
    });
    expect(requests.some((r) => r.method === "POST")).toBe(false);
    await answer.press(`${key}+Enter`);
    await expect(
      page.getByText("Synthetic claim", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Find passages", exact: true })
      .click();
    const search = page.getByLabel("Research question");
    await search.fill("Fixture question");
    await search.dispatchEvent("keydown", {
      key: "Enter",
      ctrlKey: true,
      isComposing: true,
    });
    expect(requests.some((r) => r.path.endsWith("/search"))).toBe(false);
    await search.press(`${key}+Enter`);
    await expect(page.getByText("2 unique passages")).toBeVisible();
  });

for (const width of [1280, 390])
  test(`quick actions reveal nested controls in two activations at ${width}px without executing them`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const requests = await workspace(page);
    const reached: { action: string; activations: number }[] = [];
    for (const [label, target] of [
      ["Add sources — choose files", "documents"],
      ["Focus question composer", "research-question"],
      ["Compare retrieval methods", "compare-methods"],
      ["Boolean syntax and retrieval method", "parser"],
      ["Evidence shortlist", "passage-shortlist > summary"],
      ["Answer provider and consent", "generation-provider"],
      ["Standalone follow-up query", "effective-query"],
      ["Find saved research", "saved-search"],
      ["Browse conversations", "conversation"],
    ]) {
      await command(page, label);
      await expect(page.locator(`#${target}`)).toBeFocused();
      reached.push({ action: label, activations: 2 });
    }
    await page
      .getByRole("navigation", { name: "All saved research" })
      .getByRole("button")
      .first()
      .click();
    await expect(
      page.getByText("Synthetic claim", { exact: true }),
    ).toBeVisible();
    for (const [label, target] of [
      ["Saved run provenance", "run-provenance > summary"],
      ["Based on — used and retrieved evidence", "answer-based-on > summary"],
      ...["Markdown", "BibTeX", "JSON", "CSV"].map((format) => [
        `Export saved answer as ${format}`,
        `run-export-${format.toLowerCase()}`,
      ]),
      ["Replay pinned snapshot", "replay-pinned"],
      ["Replay current snapshot", "replay-current"],
    ]) {
      await command(page, label);
      await expect(page.locator(`#${target}`)).toBeFocused();
      reached.push({ action: label, activations: 2 });
    }
    expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
    await expect(page.locator("#answer-based-on")).toContainText(
      "1 cited passage · 2 retrieved candidates",
    );
    await expect(page.locator("#answer-based-on ul").nth(0)).toContainText(
      "used source",
    );
    await expect(page.locator("#answer-based-on ul").nth(1)).toContainText(
      "candidate source",
    );
    const countPath = info.outputPath("quick-action-counts.json");
    await writeFile(countPath, JSON.stringify(reached, null, 2));
    await info.attach("measured-quick-action-counts", {
      path: countPath,
      contentType: "application/json",
    });
  });

test("search commands disclose comparison, filters, diagnostics and missing prerequisites", async ({
  page,
}) => {
  await workspace(page, "none");
  await command(page, "Filter returned passages");
  await expect(
    page.getByRole("status").filter({ hasText: /Run a passage search/ }),
  ).toBeVisible();
  await command(page, "Compare retrieval methods");
  await page.locator("#compare-methods").click();
  await expect(
    page.getByLabel("Retrieval method", { exact: true }),
  ).toHaveValue("compare");
  await page.getByLabel("Research question").fill("Fixture question");
  await page
    .getByRole("button", { name: "Search evidence", exact: true })
    .click();
  await expect(page.getByText("2 unique passages")).toBeVisible();
  for (const [label, target] of [
    ["Restore a recent query", "recent-searches > summary"],
    ["Compact or full excerpts", "excerpt-display"],
    ["Inspect passages and original sources", "search-based-on > summary"],
  ]) {
    await command(page, label);
    await expect(page.locator(`#${target}`)).toBeFocused();
  }
  await command(page, "Filter returned passages");
  await expect(page.locator("#passage-filter")).toBeFocused();
  await command(page, "Search snapshot and provenance");
  await expect(page.locator("#search-diagnostics > summary")).toBeFocused();
  await expect(page.locator("#search-diagnostics")).toContainText("snapshot");
});

test("saved lookup is collection scoped, paginated, and handles denied access", async ({
  page,
}) => {
  const requests = await workspace(page);
  await command(page, "Find saved research");
  await page.getByLabel("Find saved research").fill("sparse & dense");
  await expect(
    page.getByRole("button", { name: "Older research" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Older research" }).click();
  await expect(
    page.getByRole("button", { name: "Newest research" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      requests.some(
        (r) =>
          r.path === "/api/v1/collections/one/runs" &&
          new URLSearchParams(r.query).get("q") === "sparse & dense" &&
          new URLSearchParams(r.query).get("before") === "run",
      ),
    )
    .toBe(true);
  expect(
    requests.some((r) =>
      /^\/api\/v1\/conversations\/[^/]+\/runs$/.test(r.path),
    ),
  ).toBe(false);
  await page.route("**/collections/two/runs?*", (route) =>
    route.fulfill({
      status: 403,
      json: {
        code: "forbidden",
        message: "Access unavailable. Select another collection.",
      },
    }),
  );
  await page.getByRole("button", { name: "Collection two Private" }).click();
  await command(page, "Find saved research");
  await expect(
    page.getByText("Access unavailable. Select another collection.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "All saved research" }),
  ).not.toBeVisible();
});
