import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";
import puppeteer from "puppeteer-core";
import { snapshot } from "lighthouse";
import { preview } from "vite";
import { evidenceWorkbench } from "../ui-tests/fixtures/evidence-workbench.ts";

// Audit the built search screen with synthetic, local evidence. No external services.
const server = await preview({
  preview: { host: "127.0.0.1", port: 4175, strictPort: true },
});
let browser;
try {
  browser = await puppeteer.launch({
    executablePath: chromium.executablePath(),
    headless: true,
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  let handler;
  await evidenceWorkbench({
    route: async (_pattern, callback) => {
      handler = callback;
    },
  });
  await page.setRequestInterception(true);
  page.on("request", async (request) => {
    if (!new URL(request.url()).pathname.startsWith("/api/v1/")) {
      await request.continue();
      return;
    }
    await handler({
      request: () => ({
        url: () => request.url(),
        postDataJSON: () => JSON.parse(request.postData() || "{}"),
      }),
      fulfill: ({ json, status = 200, contentType, body }) =>
        request.respond({
          status,
          contentType: json === undefined ? contentType : "application/json",
          body: json === undefined ? body : JSON.stringify(json),
        }),
    });
  });
  await page.goto("http://127.0.0.1:4175", { waitUntil: "networkidle0" });
  await page.waitForSelector("#question");
  await page.type("#question", "retrieval evidence");
  await page.keyboard.press("Enter");
  await page.waitForSelector(".passage-list .passage-card");
  await page.evaluate(() => document.fonts.ready);
  const directory = "test-results/lighthouse-search";
  await mkdir(directory, { recursive: true });
  for (const theme of ["light", "dark"]) {
    await page.select(".theme-control select", theme);
    const result = await snapshot(page, {
      flags: {
        onlyCategories: ["accessibility"],
        formFactor: "desktop",
        screenEmulation: { disabled: true },
        logLevel: "error",
      },
    });
    await writeFile(
      `${directory}/${theme}.json`,
      JSON.stringify(result.lhr, null, 2),
    );
    const score = result.lhr.categories.accessibility.score * 100;
    console.log(`${theme}: Lighthouse accessibility ${score}`);
    const failed = Object.values(result.lhr.audits)
      .filter(
        (audit) => audit.scoreDisplayMode === "binary" && audit.score === 0,
      )
      .map((audit) => audit.id);
    assert.equal(
      score,
      100,
      `Failed accessibility audits: ${failed.join(", ")}`,
    );
  }
} finally {
  await browser?.close();
  await new Promise((resolve, reject) =>
    server.httpServer.close((error) => (error ? reject(error) : resolve())),
  );
}
