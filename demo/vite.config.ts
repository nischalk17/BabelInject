import { defineConfig } from "vitest/config";

// Project Pages are served from /<repo>/, so the base path must match the repository name.
export default defineConfig({
  base: "/agent-injection-eval/",
  build: { outDir: "dist", sourcemap: false },
  test: { environment: "jsdom", include: ["tests/**/*.test.ts"] },
});
