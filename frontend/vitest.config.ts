import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    clearMocks: true,
    // Whole-app tests use the default 1s wait; running files in parallel makes them timing-dependent.
    fileParallelism: false,
  },
});
