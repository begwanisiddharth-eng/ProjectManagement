import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { testDatabasePath } from "./tests/test-database";

const backendDir = path.resolve(__dirname, "../backend");

export default defineConfig({
  testDir: "./tests",
  globalTeardown: "./tests/global-teardown.ts",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run build && uv run --project "${backendDir}" uvicorn backend.main:app --host 127.0.0.1 --port 8000`,
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: false,
    env: { KANBAN_DB_PATH: testDatabasePath },
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
