import { defineConfig } from "@playwright/test";
const python =
  process.platform === "win32"
    ? "..\\.venv\\Scripts\\python.exe"
    : "../.venv/bin/python";
export default defineConfig({
  testDir: "./e2e",
  timeout: 120000,
  workers: 1,
  fullyParallel: false,
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }]],
  use: {
    baseURL: "http://127.0.0.1:15173",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" ../scripts/e2e_server.py`,
      url: "http://127.0.0.1:18080/health",
      env: { E2E_API_PORT: "18080" },
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 15173 --strictPort",
      url: "http://127.0.0.1:15173",
      env: { REPAIRLAB_API_TARGET: "http://127.0.0.1:18080" },
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
