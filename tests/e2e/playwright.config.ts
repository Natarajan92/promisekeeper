import { randomUUID } from "node:crypto";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { PlaywrightTestConfig } from "../../frontend/node_modules/@playwright/test";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runtime = path.join(repo, ".runtime", "e2e", randomUUID());
mkdirSync(runtime, { recursive: true });
const config: PlaywrightTestConfig = {
  testDir: path.join(repo, "tests/e2e"),
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 7_000 },
  outputDir: path.join(runtime, "results"),
  reporter: [["list"]],
  globalSetup: path.join(repo,"tests/e2e/support/globalSetup.ts"),
  use: { baseURL: "http://127.0.0.1:19000", browserName: "chromium", channel: "chrome", headless: true,
         screenshot: "only-on-failure", trace: "retain-on-failure" },
};
export default config;
