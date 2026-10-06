import { defineConfig } from "@playwright/test";

// Real Docker demo services, no synthetic routes or test identity provider.
export default defineConfig({
  testDir: "demo-tests",
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:8000", trace: "off" },
});
