import { defineConfig } from '@playwright/test';

export default defineConfig({
    // Retry on CI only.
    retries: process.env.CI ? 2 : 0,

    // Stop execution after first failed test
    maxFailures: 1,

    workers: 1,

    use: {
        viewport: { width: 1600, height: 1200 },
        // Base URL to use in actions like `await page.goto('/')`.

        baseURL: process.env.CI ? process.env.E2E_BASE_URL : 'http://localhost:8001',

        // Store downloads to disk so tests can read them
        acceptDownloads: true,

        // Collect trace when retrying the failed test.
        trace: 'retain-on-failure',

        // Collect screenshots.
        screenshot: 'only-on-failure',

        video: {
            mode: 'on-first-retry',
            size: { width: 640, height: 480 }
        }
    },

    // Glob patterns or regular expressions that match test files.
    testMatch: ['**/*.{e2e-test,e2e-spec}.{js,ts,mjs}'],

    testDir: 'e2e',

    // max timeout for each test
    timeout: 30_000
});
