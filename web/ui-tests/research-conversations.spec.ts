import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const evidence = {
  evidence_id: "e1",
  citation_id: "citation",
  title: "A retained source",
  text: "The retained passage supports this claim.",
  page_range: [2, 3],
  source_id: null,
  snapshot_id: "snapshot",
};
const savedRun = (id = "run", conversation = "conversation") => ({
  run_id: id,
  conversation_id: conversation,
  original_question:
    id === "other-run"
      ? "Another saved question"
      : "The original saved question",
  effective_query: "Pinned retrieval query",
  snapshot_id: "snapshot",
  state: "completed",
  error_code: null,
  configuration: {
    provider: "local",
    retrieval: "hybrid",
    generation: { model: "Fixture model", revision: "retained-revision" },
  },
  result: {
    elapsed_ms: 15,
    budget: { excluded: [], input_tokens: 20 },
    evidence: [evidence],
    answer: {
      status: "partial",
      claims: [
        {
          id: "claim",
          text:
            id === "other-run"
              ? "Another retained answer."
              : "An immutable saved answer.",
          evidence_ids: ["e1", "missing-passage"],
        },
      ],
      comparisons: [],
      limitations: ["Synthetic interface fixture."],
    },
  },
});
async function workspace(page: Page) {
  let state = "completed",
    failed = false;
  const posts: {
    path: string;
    body: Record<string, unknown>;
    csrf: string | undefined;
  }[] = [];
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/me"))
      json = { principal_id: "research-fixture", csrf_token: "fixture-csrf" };
    else if (path === "/api/v1/collections")
      json = [
        {
          collection_id: "one",
          title: "Research collection",
          can_manage: true,
          visibility: "private",
          active_snapshot: "snapshot",
        },
      ];
    else if (path.endsWith("/providers"))
      json = [
        {
          name: "local",
          model: "Fixture model",
          cloud: false,
          consented: true,
        },
      ];
    else if (path === "/api/v1/collections/one/conversations")
      json = [
        {
          conversation_id: "conversation",
          title: "A saved conversation",
          created_at: "2026-10-01T12:00:00Z",
        },
        {
          conversation_id: "other",
          title: "Another conversation",
          created_at: "2026-10-02T12:00:00Z",
        },
      ];
    else if (path === "/api/v1/collections/one/runs")
      json = {
        items: [
          { ...savedRun(), created_at: "2026-10-01T12:00:00Z" },
          {
            ...savedRun("other-run", "other"),
            created_at: "2026-10-02T12:00:00Z",
          },
        ],
        next_cursor: null,
      };
    else if (path.endsWith("/cancel")) {
      posts.push({
        path,
        body: {},
        csrf: route.request().headers()["x-csrf-token"],
      });
      state = "cancelled";
      return route.fulfill({ status: 204 });
    } else if (
      path === "/api/v1/conversations/conversation/runs" &&
      route.request().method() === "POST"
    ) {
      posts.push({
        path,
        body: route.request().postDataJSON(),
        csrf: route.request().headers()["x-csrf-token"],
      });
      failed = false;
      state = "queued";
      json = { ...savedRun(), state, result: null };
    } else if (path.startsWith("/api/v1/conversations/"))
      json = [
        path.includes("/other/") ? savedRun("other-run", "other") : savedRun(),
      ];
    else if (path === "/api/v1/runs/run")
      json = {
        ...savedRun(),
        state: failed ? "failed" : state,
        error_code: failed ? "provider_unavailable" : null,
        result: state === "completed" && !failed ? savedRun().result : null,
      };
    else if (path === "/api/v1/runs/other-run")
      json = savedRun("other-run", "other");
    else if (path.endsWith("/events"))
      return route.fulfill({
        contentType: "text/event-stream",
        body: `retry: 3000\nid: 1\nevent: evidence_ready\ndata: ${JSON.stringify({ run_id: "run", evidence: [evidence] })}\n\n`,
      });
    else if (path === "/api/v1/citations/citation") json = evidence;
    else if (path.endsWith("/papers")) json = { items: [], next_cursor: null };
    return route.fulfill({ json });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Cited answers", exact: true }),
  ).toBeVisible();
  return {
    posts,
    setState: (value: string) => {
      state = value;
    },
    setFailed: (value: boolean) => {
      failed = value;
    },
  };
}
async function openSaved(page: Page) {
  await page
    .getByRole("navigation", { name: "Research conversations" })
    .getByRole("button", { name: /A saved conversation/ })
    .click();
  await expect(
    page.getByText("An immutable saved answer.", { exact: true }),
  ).toBeVisible();
}
test("numbered citations support keyboard previews, source inspection, unresolved warnings, and exact conversation reopening", async ({
  page,
}) => {
  await workspace(page);
  await openSaved(page);
  const chip = page
    .locator(".claim-citations")
    .getByRole("button", { name: "Inspect citation e1", exact: true });
  await expect(chip).toHaveText("[1]");
  await chip.focus();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toContainText(evidence.text);
  await expect(tooltip).toContainText(evidence.title);
  await expect(tooltip).toContainText("Snapshot snapshot");
  await page.mouse.move(0, 0);
  await expect(tooltip).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(tooltip).toHaveCount(0);
  await expect(chip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("complementary", { name: "Evidence inspector" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(chip).toBeFocused();
  await expect(page.getByRole("note")).toContainText(
    "Unresolved citation: missing-passage",
  );
  const rail = page.getByRole("navigation", { name: "Research conversations" });
  await expect(rail.getByRole("button").first()).toContainText(
    "The original saved question",
  );
  await expect(rail.locator("time")).toHaveCount(2);
  await rail.getByRole("button", { name: /Another conversation/ }).click();
  await expect(
    page.getByText("Another retained answer.", { exact: true }),
  ).toBeVisible();
  await rail.getByRole("button", { name: /A saved conversation/ }).click();
  await expect(
    page.getByText("An immutable saved answer.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("An immutable saved answer.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".answer")).toContainText(
    "The original saved question",
  );
});
test("hover-only citation previews remain reachable and scrollable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1600 });
  await workspace(page);
  const longRun = structuredClone(savedRun());
  longRun.result.evidence[0].text =
    "A long retained passage for reading and verification. ".repeat(100);
  await page.route("**/api/v1/runs/run", (route) =>
    route.fulfill({ json: longRun }),
  );
  await openSaved(page);
  const chip = page
    .locator(".claim-citations")
    .getByRole("button", { name: "Inspect citation e1", exact: true });
  await chip.evaluate((element) => element.scrollIntoView({ block: "center" }));
  await chip.hover();
  await expect(chip).not.toBeFocused();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toBeVisible();
  const anchor = (await chip.boundingBox())!;
  await page.mouse.move(
    anchor.x + anchor.width / 2,
    anchor.y + anchor.height + 6,
  );
  await expect(tooltip).toBeVisible();
  const preview = (await tooltip.boundingBox())!;
  await page.mouse.move(preview.x + preview.width / 2, preview.y + 60);
  await page.mouse.wheel(0, 500);
  await expect
    .poll(() => tooltip.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);
  await page.mouse.move(0, 0);
  await expect(tooltip).toHaveCount(0);
});

test("failed runs explain the failure, copy details, and retry the pinned question", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const fixture = await workspace(page);
  fixture.setFailed(true);
  await page
    .getByRole("navigation", { name: "Research conversations" })
    .getByRole("button", { name: /A saved conversation/ })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "configured model is unavailable",
  );
  await page
    .getByRole("button", { name: "Copy run details", exact: true })
    .click();
  const details = JSON.parse(
    await page.evaluate(() => navigator.clipboard.readText()),
  );
  expect(details.error_code).toBe("provider_unavailable");
  expect(details.snapshot_id).toBe("snapshot");
  await expect(
    page.locator('.run-status-strip [data-state="complete"]'),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Retry research run", exact: true })
    .click();
  await expect.poll(() => fixture.posts.length).toBe(1);
  expect(fixture.posts[0].body.question).toBe("The original saved question");
  expect(fixture.posts[0].body.snapshot).toBe("historical");
  expect(fixture.posts[0].csrf).toBe("fixture-csrf");
});

test("conversation navigation waits for an in-flight submission", async ({
  page,
}) => {
  await workspace(page);
  await openSaved(page);
  let release!: () => void;
  const waiting = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    "**/api/v1/conversations/conversation/runs",
    async (route) => {
      if (route.request().method() === "POST") await waiting;
      await route.fallback();
    },
  );
  await page
    .getByLabel("Question for cited answer")
    .fill("A new research question");
  await page
    .getByRole("button", { name: "Generate cited answer", exact: true })
    .click();
  try {
    await expect(
      page.getByRole("button", { name: "Start a conversation", exact: true }),
    ).toBeDisabled();
    for (const button of await page
      .getByRole("navigation", { name: "Research conversations" })
      .getByRole("button")
      .all())
      await expect(button).toBeDisabled();
  } finally {
    release();
  }
  await expect(
    page.getByRole("button", { name: "Start a conversation", exact: true }),
  ).toBeEnabled();
});

test("older conversation previews load from authorized history without claiming they are empty", async ({
  page,
}) => {
  await workspace(page);
  await page.route("**/api/v1/collections/one/runs?limit=100", (route) =>
    route.fulfill({
      json: {
        items: [savedRun("other-run", "other")],
        next_cursor: "older-page",
      },
    }),
  );
  await page.reload();
  const conversation = page
    .getByRole("navigation", { name: "Research conversations" })
    .getByRole("button", { name: /A saved conversation/ });
  await expect(conversation).toContainText("Open to load the latest question");
  await conversation.click();
  await expect(conversation).toContainText("The original saved question");
  await expect(
    page.getByText("An immutable saved answer.", { exact: true }),
  ).toBeVisible();
});
test("status strip follows the existing live run stages and cancel uses the authenticated endpoint", async ({
  page,
}) => {
  const fixture = await workspace(page);
  fixture.setState("retrieving");
  await page
    .getByRole("navigation", { name: "Research conversations" })
    .getByRole("button", { name: /A saved conversation/ })
    .click();
  const strip = page.getByRole("list", { name: "Research progress" });
  await expect(strip.locator('[aria-current="step"]')).toContainText(
    "Retrieving",
  );
  fixture.setState("generating");
  await expect(strip.locator('[aria-current="step"]')).toContainText(
    "Generating",
    { timeout: 10000 },
  );
  await expect(page.getByText(evidence.text, { exact: true })).toBeVisible();
  fixture.setState("validating");
  await expect(strip.locator('[aria-current="step"]')).toContainText(
    "Validating",
    { timeout: 10000 },
  );
  await page.getByRole("button", { name: "Cancel run", exact: true }).click();
  await expect.poll(() => fixture.posts.length).toBe(1);
  expect(fixture.posts[0].path).toBe("/api/v1/runs/run/cancel");
  expect(fixture.posts[0].csrf).toBe("fixture-csrf");
  await expect(
    page.getByText("This run was cancelled. No late answer will be published."),
  ).toBeVisible();
});
for (const width of [1440, 390])
  test(`conversation reading layout and citations pass axe in both themes at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    await workspace(page);
    await openSaved(page);
    await expect(
      page
        .getByRole("list", { name: "Research progress" })
        .locator('[aria-current="step"]'),
    ).toContainText("Saved");
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
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      if (width === 390)
        expect(
          await page
            .locator(".claim-citations")
            .boundingBox()
            .then((box) => box!.y),
        ).toBeGreaterThan(
          await page
            .locator(".claim > p")
            .boundingBox()
            .then((box) => box!.y),
        );
      await page.screenshot({
        path: info.outputPath(`conversations-${theme}.png`),
        fullPage: true,
      });
    }
  });
