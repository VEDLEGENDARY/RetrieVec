import { defineConfig } from "@playwright/test";

// Interaction tests use synthetic HTTP fixtures; workspace.spec.ts covers the real services.
export default defineConfig({
  testDir: "ui-tests",
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  webServer: {
    command: "npm run dev -- --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
  },
});
