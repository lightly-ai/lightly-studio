import { defineConfig } from '@playwright/test';
import playwrightConfig from './playwright.config';

export default defineConfig({
    ...playwrightConfig,
    retries: 0,
    projects: [
        {
            name: 'media-benchmark-images',
            testDir: './e2e/media-benchmark',
            testMatch: 'images.e2e-benchmark.ts'
        },
        {
            name: 'media-benchmark-videos',
            testDir: './e2e/media-benchmark',
            testMatch: 'videos.e2e-benchmark.ts'
        }
    ],
    timeout: 20 * 60_000
});
