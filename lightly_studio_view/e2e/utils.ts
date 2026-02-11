import { expect, Page, Request, test as base } from '@playwright/test';
import {
    AnnotationsPage,
    AnnotationDetailsPage,
    SamplesPage,
    SampleDetailsPage,
    CaptionsPage,
    VideosPage,
    VideoFramesPage,
    VideoFrameDetailsPage
} from './pages';

export async function gotoFirstPage(page: Page): Promise<void> {
    await page.goto('/');
    await expect(page.getByTestId('sample-grid-item').first()).toBeVisible({ timeout: 10000 });
}

type Pages = {
    annotationsPage: AnnotationsPage;
    annotationDetailsPage: AnnotationDetailsPage;
    samplesPage: SamplesPage;
    sampleDetailsPage: SampleDetailsPage;
    captionsPage: CaptionsPage;
    captionsVideoFramePage: CaptionsPage;
    videosPage: VideosPage;
    videoFramesPage: VideoFramesPage;
    videoFrameDetailsPage: VideoFrameDetailsPage;
};

export const test = base.extend<Pages>({
    annotationsPage: async ({ page }, use) => {
        // Set up the fixture.
        const annotationsPage = new AnnotationsPage(page);
        await annotationsPage.goto();

        // Use the fixture value in the test.
        await use(annotationsPage);
    },

    annotationDetailsPage: async ({ page }, use) => {
        // Set up the fixture.
        const annotationDetailsPage = new AnnotationDetailsPage(page);
        await use(annotationDetailsPage);
    },

    samplesPage: async ({ page }, use) => {
        // Set up the fixture.
        const samplesPage = new SamplesPage(page);
        await samplesPage.goto();

        // Use the fixture value in the test.
        await use(samplesPage);
    },

    sampleDetailsPage: async ({ page }, use) => {
        // Set up the fixture.
        const sampleDetailsPage = new SampleDetailsPage(page);
        await use(sampleDetailsPage);
    },
    captionsPage: async ({ page }, use) => {
        // Set up the fixture.
        const captionsPage = new CaptionsPage(page);
        await captionsPage.goto();

        // Use the fixture value in the test.
        await use(captionsPage);
    },
    captionsVideoFramePage: async ({ page }, use) => {
        // Set up the fixture.
        const captionsPage = new CaptionsPage(page);
        await captionsPage.gotoVideoFrameCaptions();

        // Use the fixture value in the test.
        await use(captionsPage);
    },

    videosPage: async ({ page }, use) => {
        // Set up the fixture.
        const videosPage = new VideosPage(page);
        await videosPage.goto();

        // Use the fixture value in the test.
        await use(videosPage);
    },

    videoFramesPage: async ({ page }, use) => {
        // Set up the fixture.
        const videoFramesPage = new VideoFramesPage(page);
        await videoFramesPage.goto();

        // Use the fixture value in the test.
        await use(videoFramesPage);
    },
    videoFrameDetailsPage: async ({ page }, use) => {
        const videoFrameDetailsPage = new VideoFrameDetailsPage(page);
        await use(videoFrameDetailsPage);
    }
});

export async function pressButton(page: Page, buttonId: string): Promise<void> {
    const button = page.getByTestId(buttonId);
    await expect(button).toBeEnabled();
    await button.click();
}

/**
 * Wait until no requests matching `urlPattern` are in-flight and no new ones
 * have started for `timeoutMs` milliseconds.
 *
 * This is used to work around DuckDB's concurrency limitations: concurrent
 * short-lived sessions (e.g. a GET and a PUT to /annotations) can cause FK
 * constraint violations. By waiting for all matching requests to settle before
 * triggering a new action, we ensure only one session is active at a time.
 */
export async function waitForRequestsToSettle(
    page: Page,
    urlPattern: string,
    timeoutMs: number = 1000
): Promise<void> {
    let inFlight = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    return new Promise<void>((resolve) => {
        // Start (or restart) a countdown. If it fires without being canceled
        // by a new request, we consider the network settled and resolve.
        const startIdleCountdown = () => {
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => {
                cleanup();
                resolve();
            }, timeoutMs);
        };

        // When a matching request starts, track it and cancel the countdown.
        const onRequest = (request: Request) => {
            if (request.url().includes(urlPattern)) {
                inFlight++;
                if (timer) clearTimeout(timer);
            }
        };

        // When a matching request finishes (or fails), stop tracking it.
        // If all matching requests are done, restart the idle countdown.
        const onRequestDone = (request: Request) => {
            if (request.url().includes(urlPattern)) {
                inFlight = Math.max(0, inFlight - 1);
                if (inFlight === 0) {
                    startIdleCountdown();
                }
            }
        };

        // Remove all event listeners to avoid leaks.
        const cleanup = () => {
            page.off('request', onRequest);
            page.off('requestfinished', onRequestDone);
            page.off('requestfailed', onRequestDone);
        };

        page.on('request', onRequest);
        page.on('requestfinished', onRequestDone);
        page.on('requestfailed', onRequestDone);

        // Kick off the countdown immediately in case no matching requests
        // are in-flight when this function is called.
        startIdleCountdown();
    });
}


export { expect } from '@playwright/test';
