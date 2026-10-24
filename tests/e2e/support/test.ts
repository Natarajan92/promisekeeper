// Resolve the same Playwright installation as the frontend runner; do not install a second copy.
import { createRequire } from "node:module";
import type * as Playwright from "../../../frontend/node_modules/@playwright/test";
const runner = createRequire(new URL("../../../frontend/package.json", import.meta.url))("@playwright/test") as typeof Playwright;
export const test = runner.test;
export const expect = runner.expect;
export type { APIRequestContext, Page } from "../../../frontend/node_modules/@playwright/test";
