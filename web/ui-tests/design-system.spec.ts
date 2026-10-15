import { test, expect, type Page, type Locator } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";

// Synthetic UI fixtures only. No paper, retrieval, generation, or timing claims.
const collection = {
  collection_id: "one",
  title: "Design review collection",
  visibility: "private",
  can_manage: true,
  active_snapshot: "snapshot",
};
const evidence = {
  evidence_id: "e1",
  citation_id: "citation",
  chunk_id: "structured",
  evidence_object_id: "object",
  title: "Synthetic source",
  text: "Synthetic passage for interface review. This is not research evidence.",
  page_range: [1, 1],
  source_id: null,
  snapshot_id: "snapshot",
};
const hit = {
  ...evidence,
  rank: 1,
  bm25_score: 1,
  cosine_score: 0.5,
  rrf_score: 0.01,
};

async function contrast(locator: Locator, property = "color") {
  return locator.evaluate((node, property) => {
    const rgba = (s: string) => {
      const values = s.match(/[\d.]+/g)!.map(Number);
      return [values[0], values[1], values[2], values[3] ?? 1];
    };
    const blend = (fg: number[], bg: number[]) =>
      fg
        .slice(0, 3)
        .map((v, i) => v * fg[3] + bg[i] * (1 - fg[3]))
        .concat(1);
    const layers: number[][] = [];
    for (
      let current: Element | null = node;
      current;
      current = current.parentElement
    ) {
      const style = getComputedStyle(current);
      // Reject unsupported surfaces rather than reporting a guessed passing ratio.
      if (style.backgroundImage !== "none" || Number(style.opacity) !== 1)
        throw new Error("Contrast requires an opaque, image-free text surface");
      layers.push(rgba(style.backgroundColor));
    }
    let background = [255, 255, 255, 1];
    for (const layer of layers.reverse()) background = blend(layer, background);
    const foreground = blend(
      rgba(getComputedStyle(node).getPropertyValue(property)),
      background,
    );
    const luminance = (rgb: number[]) =>
      rgb
        .slice(0, 3)
        .map((v) => {
          const s = v / 255;
          return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        })
        .reduce(
          (sum, value, i) => sum + value * [0.2126, 0.7152, 0.0722][i],
          0,
        );
    const a = luminance(foreground),
      b = luminance(background);
    return {
      foreground: foreground.slice(0, 3),
      background: background.slice(0, 3),
      ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
    };
  }, property);
}

for (const width of [1280, 390])
  for (const colorScheme of ["light", "dark"] as const) {
    test(`screen inventory ${width} ${colorScheme}`, async ({ page }, info) => {
      test.setTimeout(240000);
      page.setDefaultTimeout(10000);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
      const materialMedia = await page.context().newCDPSession(page);
      await materialMedia.send("Emulation.setEmulatedMedia", {
        features: [
          { name: "prefers-color-scheme", value: colorScheme },
          { name: "prefers-reduced-motion", value: "reduce" },
          { name: "prefers-reduced-transparency", value: "no-preference" },
        ],
      });
      let signedIn = true,
        empty = false,
        snapshot = true,
        archived = false;
      let jobs = false,
        cloud = false,
        runState = "completed",
        kind = "table",
        structuredError = false;
      let releaseSession!: () => void;
      const sessionGate = new Promise<void>((resolve) => {
        releaseSession = resolve;
      });
      await page.route("**/api/v1/**", async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith("/papers"))
          return route.fulfill({
            json: { items: [], next_cursor: null },
          });
        let json: unknown = [];
        if (path.endsWith("/me")) {
          await sessionGate;
          if (!signedIn)
            return route.fulfill({
              status: 401,
              json: {
                code: "unauthenticated",
                message: "Sign in to continue.",
              },
            });
          json = { principal_id: "design-fixture", csrf_token: "fixture" };
        } else if (path === "/api/v1/collections")
          json =
            empty || archived
              ? []
              : [
                  {
                    ...collection,
                    active_snapshot: snapshot ? "snapshot" : null,
                  },
                ];
        else if (
          path === "/api/v1/collections/one" &&
          route.request().method() === "DELETE"
        ) {
          archived = true;
          return route.fulfill({ status: 204 });
        } else if (path.endsWith("/jobs"))
          json = jobs
            ? [
                "queued",
                "running",
                "retry_wait",
                "succeeded",
                "failed",
                "cancelled",
              ].map((state) => ({
                job_id: state,
                state,
                stage: "extract",
                error_code: state === "failed" ? "ocr_required" : null,
                output_snapshot: state === "succeeded" ? "snapshot" : null,
              }))
            : [];
        else if (path.endsWith("/providers"))
          json = cloud
            ? [
                {
                  name: "cloud",
                  model: "Synthetic cloud provider",
                  cloud: true,
                  consented: false,
                },
              ]
            : [];
        else if (path === "/api/v1/search")
          json = {
            collection_id: "one",
            snapshot_id: "snapshot",
            query: "Synthetic question",
            mode: "free_text",
            results: {
              hybrid: {
                hits: [
                  hit,
                  {
                    ...hit,
                    chunk_id: "ordinary",
                    evidence_object_id: undefined,
                    title: "Ordinary synthetic source",
                    rank: 2,
                    source_id: "original",
                  },
                ],
                total_matches: 2,
                configuration: {},
              },
            },
          };
        else if (path.endsWith("/runs") && path.includes("/collections/"))
          json = {
            items: [
              {
                run_id: "run",
                conversation_id: "conversation",
                original_question: "Synthetic review question",
                state: runState,
                created_at: "2026-10-04T12:00:00Z",
              },
            ],
            next_cursor: null,
          };
        else if (path === "/api/v1/runs/run")
          json = {
            run_id: "run",
            conversation_id: "conversation",
            original_question: "Synthetic review question",
            effective_query: "Synthetic review question",
            snapshot_id: "snapshot",
            state: runState,
            error_code: "invalid_answer",
            configuration: {
              provider: "fixture",
              retrieval: "hybrid",
              generation: { model: "fixture", revision: "fixture" },
            },
            result:
              runState === "completed"
                ? {
                    elapsed_ms: 0,
                    evidence: [evidence],
                    budget: { input_tokens: 0, excluded: [] },
                    answer: {
                      status: "partial",
                      claims: [
                        {
                          id: "claim",
                          text: "Synthetic claim for layout review only.",
                          evidence_ids: ["e1"],
                        },
                      ],
                      comparisons: [],
                      limitations: ["Synthetic data; no quality inference."],
                    },
                  }
                : null,
          };
        else if (path.endsWith("/events"))
          return route.fulfill({
            contentType: "text/event-stream",
            body: ": fixture\n\n",
          });
        else if (path === "/api/v1/citations/citation") json = evidence;
        else if (path.endsWith("/images/page"))
          return route.fulfill({
            contentType: "image/svg+xml",
            body: '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300"><rect width="600" height="300" fill="white"/><text x="40" y="80" fill="black" font-size="24">Synthetic source page — UI fixture</text></svg>',
          });
        else if (path.includes("/evidence/structured")) {
          if (structuredError)
            return route.fulfill({
              status: 503,
              json: { code: "unavailable" },
            });
          const content =
            kind === "table"
              ? {
                  kind,
                  rows: 2,
                  columns: 2,
                  caption: "Synthetic table",
                  footnotes: ["Fixture only."],
                  cells: [
                    {
                      row: 0,
                      column: 0,
                      row_span: 1,
                      column_span: 2,
                      role: "header",
                      text: "Synthetic header",
                      missing: false,
                      ambiguous: false,
                    },
                  ],
                }
              : kind === "equation"
                ? {
                    kind,
                    label: "Synthetic equation",
                    transcription: "a + b = c",
                    definitions: ["Symbol definitions are fixture text."],
                  }
                : kind === "figure"
                  ? {
                      kind,
                      caption: "Synthetic figure",
                      observations: [
                        {
                          text: "Fixture observation",
                          basis: "visual",
                          uncertain: true,
                        },
                      ],
                    }
                  : { kind: "prose", text: evidence.text };
          json = {
            content,
            derivation: "extracted",
            review: { status: "pending" },
            warnings: ["Synthetic extraction warning."],
            raw_output: "Synthetic raw extraction.",
            synthesis_allowed: false,
            locator: {
              page: 1,
              display_box: [30, 30, 570, 120],
              display_size: [600, 300],
            },
          };
        } else if (path === "/api/v1/sources/original")
          return route.fulfill({
            contentType: "text/html",
            body: "<html lang='en'><title>Synthetic original</title><body><p>Synthetic original source preview.</p></body></html>",
          });
        return route.fulfill({ json });
      });
      const screens: string[] = [];
      const ratios: Record<string, unknown> = {};
      async function capture(name: string, scan = true) {
        await page.mouse.move(0, 0);
        await page.evaluate(() => window.scrollTo(0, 0));
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          `${name}: horizontal overflow`,
        ).toBe(true);
        const path = info.outputPath(`${name}.png`);
        await page.screenshot({ path, fullPage: true, animations: "disabled" });
        await info.attach(name, { path, contentType: "image/png" });
        screens.push(name);
        if (scan) {
          const result = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze();
          expect(result.violations, `${name}: axe`).toEqual([]);
        }
      }
      async function measure(
        name: string,
        target: Locator,
        property = "color",
        minimum = 4.5,
      ) {
        await expect(target).toBeVisible();
        const result = await contrast(target, property);
        ratios[name] = result;
        expect(result.ratio, name).toBeGreaterThanOrEqual(minimum);
      }
      const sections = page.getByRole("navigation", {
        name: "Workspace sections",
      });
      async function section(name: string) {
        await sections.getByRole("button", { name, exact: true }).click();
      }
      async function ready() {
        await expect(
          page.getByRole("heading", { name: collection.title, exact: true }),
        ).toBeVisible();
      }
      await page.goto("/");
      await expect(page.getByText("Opening your workspace…")).toBeVisible();
      await capture("opening-workspace", false);
      releaseSession();
      await ready();
      signedIn = false;
      await page.reload();
      await expect(page.getByRole("link", { name: /Sign in/ })).toBeVisible();
      await capture("signed-out-welcome");
      signedIn = true;
      empty = true;
      await page.reload();
      await expect(
        page.getByRole("heading", { name: "Start with a collection" }),
      ).toBeVisible();
      await capture("empty-workspace");
      empty = false;
      snapshot = false;
      await page.reload();
      await ready();
      await capture("collection-awaiting-sources");
      snapshot = true;
      await page.reload();
      await ready();
      await capture("workspace-search");
      await page.getByText("More search options", { exact: true }).click();
      await capture("search-options");
      await page.getByText("More search options", { exact: true }).click();
      await page.locator(".skip").focus();
      await measure("skip-link", page.locator(".skip"));
      await measure("footer", page.locator("footer"));
      const question = page.getByLabel("Research question");
      await measure("control-boundary", question, "border-top-color", 3);
      await question.hover();
      await measure("control-hover-boundary", question, "border-top-color", 3);
      const currentDestination = sections.getByRole("button", {
        name: "Ask",
        exact: true,
      });
      await expect(currentDestination).not.toHaveCSS("border-top-width", "0px");
      await measure(
        "destination-selection",
        currentDestination,
        "border-top-color",
        3,
      );
      await question.focus();
      await expect(question).toHaveCSS("outline-style", "solid");
      await measure("input-focus", question, "outline-color", 3);
      const nativeTheme = await page
        .locator("html")
        .evaluate((node) => getComputedStyle(node).colorScheme);
      expect(nativeTheme).toBe(colorScheme);
      const meta = await page
        .locator(
          `meta[name="theme-color"][media="(prefers-color-scheme: ${colorScheme})"]`,
        )
        .getAttribute("content");
      expect(
        await page
          .locator("html")
          .evaluate((node) =>
            getComputedStyle(node).getPropertyValue("--canvas").trim(),
          ),
      ).toBe(meta);
      await question.fill("Synthetic question");
      await page
        .getByRole("button", { name: "Search evidence", exact: true })
        .click();
      await expect(page.getByText("2 unique passages")).toBeVisible();
      await capture("search-results");
      await page.locator("#search-based-on > summary").click();
      await capture("search-based-on");
      await page.locator("#search-based-on > summary").click();
      await page.getByText("More evidence options", { exact: true }).click();
      await page.locator(".recent-searches > summary").click();
      await capture("recent-searches");
      await page
        .getByRole("button", { name: "Shortlist passage", exact: true })
        .first()
        .click();
      await page.locator(".evidence-tray > summary").click();
      await capture("evidence-shortlist");
      const structuredHit = page
        .getByRole("button", { name: /^Synthetic source/ })
        .first();
      await structuredHit.click();
      await expect(
        page.getByRole("table", { name: "Synthetic table" }),
      ).toBeVisible();
      await capture("search-inspector-table");
      for (const next of ["equation", "figure", "prose"]) {
        await page.keyboard.press("Escape");
        kind = next;
        await structuredHit.click();
        await expect(
          page.getByRole("region", { name: "Structured source evidence" }),
        ).toBeVisible();
        await page.getByText("Raw extraction output", { exact: true }).click();
        await capture(`structured-${next}`);
      }
      await page.keyboard.press("Escape");
      structuredError = true;
      await structuredHit.click();
      await expect(page.getByRole("alert")).toContainText(
        "Evidence is unavailable",
      );
      await capture("structured-evidence-unavailable");
      await page.keyboard.press("Escape");
      structuredError = false;
      await page
        .getByRole("button", { name: /^Ordinary synthetic source/ })
        .first()
        .click();
      await expect(page.getByTitle("Original source preview")).toBeVisible();
      await capture("original-source-preview");
      await page.keyboard.press("Escape");
      await page.getByText("More result options", { exact: true }).click();
      await page.getByLabel("Filter returned passages").fill("no-match");
      await capture("search-no-matches");
      await section("Sources");
      await page.getByText("Collection details", { exact: true }).click();
      await capture("collection-details-and-sources");
      await measure(
        "diagnostic-code",
        page
          .locator(".diagnostics code")
          .filter({ hasText: "snapshot" })
          .first(),
      );
      const file = page.getByLabel("Choose documents", { exact: true });
      await file.setInputFiles([
        {
          name: "invalid.exe",
          mimeType: "application/octet-stream",
          buffer: Buffer.from("fixture"),
        },
        {
          name: "notes.txt",
          mimeType: "text/plain",
          buffer: Buffer.from("Synthetic review source"),
        },
      ]);
      await expect(file).toHaveAttribute("aria-invalid", "true");
      const associations = await file.getAttribute("aria-describedby");
      expect(associations).toContain("documents-description");
      expect(associations).toContain("documents-error");
      await capture("upload-review-error");
      await measure("file-error", page.locator(".upload-queue .file-error"));
      const disabled = page.getByRole("button", {
        name: "Upload documents",
        exact: true,
      });
      const before = await disabled.evaluate((node) => {
        const s = getComputedStyle(node);
        return [s.backgroundColor, s.borderColor, s.boxShadow];
      });
      await disabled.hover({ force: true });
      expect(
        await disabled.evaluate((node) => {
          const s = getComputedStyle(node);
          return [s.backgroundColor, s.borderColor, s.boxShadow];
        }),
      ).toEqual(before);
      jobs = true;
      await page.reload();
      await ready();
      await expect(
        page.getByText("Waiting to retry", { exact: true }),
      ).toBeVisible();
      await capture("source-processing-states");
      await measure("status-badge", page.locator(".status-badge").first());
      await section("Ask");
      await page.getByRole("button", { name: "Answer", exact: true }).click();
      await expect(
        page.getByRole("heading", { name: "Cited answers" }),
      ).toBeVisible();
      await capture("cited-answers-no-provider");
      cloud = true;
      await page.reload();
      await ready();
      await page.getByRole("button", { name: "Answer", exact: true }).click();
      await expect(
        page.getByRole("button", { name: /Allow this cloud provider/ }),
      ).toBeVisible();
      await capture("cited-answers-cloud-consent");
      await page.getByText("More answer options", { exact: true }).click();
      await capture("answer-options");
      await section("Saved research");
      await expect(
        page.getByRole("button", { name: /Synthetic review question/ }).first(),
      ).toBeVisible();
      await capture("saved-research");
      await page
        .getByRole("button", { name: /Synthetic review question/ })
        .first()
        .click();
      await expect(
        page.getByText("Synthetic claim for layout review only."),
      ).toBeVisible();
      await capture("saved-answer");
      await page.locator("#answer-based-on > summary").click();
      await capture("answer-based-on");
      await page.locator("#answer-based-on > summary").click();
      await page.getByText("More run options", { exact: true }).click();
      await page.locator("#run-provenance > summary").click();
      await capture("run-options-and-provenance");
      await measure("answer-status", page.locator(".answer-status"));
      await page
        .getByRole("button", { name: "Inspect citation e1", exact: true })
        .last()
        .click();
      await expect(
        page.getByRole("complementary", { name: "Evidence inspector" }),
      ).toBeFocused();
      await capture("citation-inspector");
      await page.keyboard.press("Escape");
      for (const state of ["generating", "failed", "cancelled"]) {
        runState = state;
        await page.reload();
        await ready();
        await expect(page.locator(".answer")).toBeVisible();
        await capture(`research-${state}`);
      }
      await page.keyboard.press("Control+k");
      await expect(page.getByRole("dialog")).toBeVisible();
      await capture("quick-actions");
      await page
        .getByRole("combobox", { name: "Find actions and collections" })
        .fill("no-match");
      await capture("quick-actions-no-matches");
      await page.keyboard.press("Escape");
      if (width === 390) {
        await page.getByRole("button", { name: "Open navigation" }).click();
        await capture("mobile-navigation");
        await page.keyboard.press("Escape");
      }
      await page
        .getByRole("button", { name: "Archive collection", exact: true })
        .click();
      await expect(
        page.getByRole("button", { name: "Undo archive" }),
      ).toBeVisible();
      await capture("archive-undo");
      // Supplemental accessibility modes, distinct from the four baseline inventories.
      await page.emulateMedia({ forcedColors: "active" });
      await page.keyboard.press("Control+k");
      const commandInput = page.getByRole("combobox", {
        name: "Find actions and collections",
      });
      await expect(commandInput).toBeFocused();
      await expect(commandInput).toHaveCSS("outline-style", "solid");
      await capture("forced-colors-dialog", false);
      await page.keyboard.press("Escape");
      await page.emulateMedia({ forcedColors: "none" });
      if (width === 1280) {
        await page.setViewportSize({ width: 640, height: 900 });
        await capture("reflow-640-empty-workspace", false);
        await page.setViewportSize({ width, height: 900 });
      }
      const durations = await page
        .getByRole("button", { name: /Quick actions/ })
        .evaluate((node) =>
          getComputedStyle(node).transitionDuration.split(",").map(parseFloat),
        );
      expect(durations.every((value) => value <= 0.00001)).toBe(true);
      const report = JSON.stringify(
        { width, colorScheme, synthetic: true, screens, ratios },
        null,
        2,
      );
      const reportPath = info.outputPath("screen-and-contrast-report.json");
      await writeFile(reportPath, report);
      await info.attach("screen-and-contrast-report", {
        path: reportPath,
        contentType: "application/json",
      });
    });
  }
