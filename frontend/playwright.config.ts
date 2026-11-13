import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for ProjectProof AI end-to-end tests.
 * Three scenarios:
 *  1. Happy Path (Student → Company → Public Verification)
 *  2. Revocation Path (Certificate revoked; verification shows "Revoked")
 *  3. Mobile/Accessibility (360 px viewport, visible focus, ARIA labels)
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Maximum time one test can run */
  timeout: 60_000,
  /* Fail the build on CI if you accidentally left test.only */
  forbidOnly: !!process.env['CI'],
  /* Retry on CI only */
  retries: process.env['CI'] ? 2 : 0,
  /* Run tests sequentially (stateful backend) */
  workers: 1,
  /* Reporter */
  reporter: [['html', { outputFolder: 'playwright-report', open: 'never' }], ['list']],

  use: {
    /* The URL of the running frontend dev server */
    baseURL: process.env['PLAYWRIGHT_BASE_URL'] ?? 'http://localhost:5173',
    /* Capture trace on first retry */
    trace: 'on-first-retry',
    /* Capture screenshot on failure */
    screenshot: 'only-on-failure',
    /* Non-negotiable rule 1: verification pages must not be served from cache */
    extraHTTPHeaders: { 'Cache-Control': 'no-store' },
  },

  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-360',
      use: {
        ...devices['Galaxy S9+'],
        viewport: { width: 360, height: 740 },
      },
    },
  ],

  /* Start the Vite dev server before tests if not already running */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env['CI'],
    timeout: 60_000,
  },
});
