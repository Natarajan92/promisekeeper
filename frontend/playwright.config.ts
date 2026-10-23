import { defineConfig } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const runtime = path.join(repo, ".runtime", "e2e", randomUUID());
mkdirSync(runtime, { recursive: true });

// Declarative real-API lifecycle. The CLI/server and journeys arrive in later gates.
export default defineConfig({
  testDir: path.join(repo, "tests", "e2e"),
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8000", headless: true },
  webServer: {
    command: "uv run --project backend python -m promisekeeper.cli serve --host 127.0.0.1 --port 8000 --workers 1",
    cwd: repo,
    url: "http://127.0.0.1:8000/api/v1/health",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      PK_AGENT_MODE: "STUB",
      PK_DB_PATH: path.join(runtime, "isolated.sqlite"),
      UV_CACHE_DIR: path.join(repo, ".runtime", "uv-cache"),
      UV_PYTHON_INSTALL_DIR: path.join(repo, ".runtime", "python"),
    },
  },
});
