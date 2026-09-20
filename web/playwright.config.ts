import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  timeout: 120000,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8000", trace: "retain-on-failure" },
  webServer: {
    command: "python ../python/tests/serve_workspace.py",
    url: "http://127.0.0.1:8000/healthz",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
