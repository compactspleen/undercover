import { defineConfig } from "@playwright/test";

// Its own ports, so the tests never touch `npm run dev` or undercover.db.
const BACKEND_URL = "http://127.0.0.1:8100";
const DASHBOARD_URL = "http://localhost:5174";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  // The tests share one backend and its database.
  workers: 1,
  use: { baseURL: DASHBOARD_URL },
  webServer: [
    {
      command: "uv run -m uvicorn backend.main:app --port 8100",
      url: `${BACKEND_URL}/api/health`,
      // Playwright empties e2e/test-results before it starts the servers,
      // so the backend creates a fresh database on every run.
      env: { UNDERCOVER_DB: "e2e/test-results/undercover.db" },
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: DASHBOARD_URL,
      env: { BACKEND_URL },
      reuseExistingServer: false,
    },
  ],
});
