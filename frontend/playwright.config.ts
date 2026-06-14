import { defineConfig } from "@playwright/test";
export default defineConfig({ testDir: "./e2e", use: { headless: true }, webServer: [
  { command: "npm run dev:customer", port: 5173, reuseExistingServer: true },
  { command: "npm run dev:admin", port: 5174, reuseExistingServer: true },
  { command: "npm run dev:kitchen", port: 5175, reuseExistingServer: true },
  { command: "npm run dev:staff", port: 5176, reuseExistingServer: true }
] });
