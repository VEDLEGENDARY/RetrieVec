import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { copyFile, mkdir } from "node:fs/promises";

export default defineConfig({
  plugins: [
    tailwindcss(),
    {
      name: "results-static-route",
      async closeBundle() {
        await mkdir("dist/results", { recursive: true });
        await copyFile("dist/index.html", "dist/results/index.html");
      },
    },
  ],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
    },
  },
});
