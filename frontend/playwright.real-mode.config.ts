import { defineConfig } from "@playwright/test";
const python =
  process.platform === "win32"
    ? "..\\.venv\\Scripts\\python.exe"
    : "../.venv/bin/python";
export default defineConfig({
  testDir: "./e2e-real",
  timeout: 120000,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results-real/results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:15184",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${python}" ../scripts/e2e_server.py`,
      url: "http://127.0.0.1:18081/health",
      env: { E2E_API_PORT: "18081", E2E_MOCK_DEEPSEEK: "true" },
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 15184 --strictPort",
      url: "http://127.0.0.1:15184",
      env: { REPAIRLAB_API_TARGET: "http://127.0.0.1:18081" },
      timeout: 60000,
    },
  ],
});
