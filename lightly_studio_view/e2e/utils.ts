import { expect, type Locator, Page, test as base } from '@playwright/test';
import type { Request } from '@playwright/test';
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
import { NETWORK_PRESETS, type NetworkPreset } from './constants';

export { expect };

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
        // For a video dataset, captions are on the third menu level (index 2).
        await captionsPage.goto(2);

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

/**
 * Measures when a specific element is actually rendered (painted) on screen.
 *
 * Unlike LCP which measures the largest content paint, this function measures
 * when a specific element becomes visible and painted in the viewport.
 *
 * Implementation details:
 * - Waits for the element to be attached to the DOM (timeout: 10 seconds)
 * - Uses the element's data-testid attribute to identify it in the page context
 * - Uses IntersectionObserver to detect when the element enters the viewport
 * - Threshold of 0.1 means at least 10% of the element must be visible
 * - Uses requestAnimationFrame to ensure the browser has completed painting
 * - Returns performance.now() timestamp in milliseconds from navigation start
 * - Falls back to current time if element is not found
 *
 * Use cases:
 * - Measuring render time of specific UI components (grids, images, etc.)
 * - Different from LCP as it targets specific elements, not the largest one
 * - Useful for measuring time-to-interactive for critical UI elements
 *
 * @param page - Playwright Page object
 * @param locator - Playwright Locator for the element to measure
 * @returns Promise resolving to render time in milliseconds from navigation start
 */
export async function measureElementRendering(page: Page, locator: Locator): Promise<number> {
    await locator.waitFor({ state: 'attached', timeout: 10000 });
    const testId = await locator.getAttribute('data-testid');
    if (!testId) {
        throw new Error('Element must have a data-testid attribute for performance measurement');
    }
    const selector = `[data-testid="${testId}"]`;

    return page.evaluate((sel) => {
        return new Promise<number>((resolve) => {
            const element = document.querySelector(sel);
            if (!element) {
                resolve(performance.now());
                return;
            }

            const observer = new IntersectionObserver(
                (entries) => {
                    if (entries[0].isIntersecting && entries[0].intersectionRatio > 0) {
                        observer.disconnect();
                        // Use requestAnimationFrame to ensure paint has occurred
                        requestAnimationFrame(() => {
                            resolve(performance.now());
                        });
                    }
                },
                { threshold: 0.1 }
            );
            observer.observe(element);
        });
    }, selector);
}

/**
 * Calculates the median value from an array of numbers.
 *
 * @param values - Array of numbers
 * @returns Median value
 */
function calculateMedian(values: number[]): number {
    if (values.length === 0) throw new Error('Cannot calculate median of empty array');

    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);

    if (sorted.length % 2 === 0) {
        return (sorted[mid - 1] + sorted[mid]) / 2;
    }
    return sorted[mid];
}

/**
 * Measures element rendering time multiple times and returns statistics including the median.
 * This provides more stable performance measurements by reducing the impact of outliers.
 *
 * @param measureFn - Async function that performs a single measurement
 * @param iterations - Number of times to run the measurement (default: 5)
 * @returns Object containing all measurements, median, min, max, and average
 *
 * @example
 * const result = await measureWithMedian(async () => {
 *   await page.goto('/samples');
 *   return await measureElementRendering(page, samplesPage.getSampleByIndex(1));
 * });
 * console.log(result.median); // 1234
 */
export async function measureWithMedian(
    measureFn: () => Promise<number>,
    iterations: number = 5
): Promise<{
    measurements: number[];
    median: number;
    min: number;
    max: number;
    average: number;
}> {
    const measurements: number[] = [];

    for (let i = 0; i < iterations; i++) {
        const measurement = await measureFn();
        measurements.push(measurement);
    }

    return {
        measurements,
        median: calculateMedian(measurements),
        min: Math.min(...measurements),
        max: Math.max(...measurements),
        average: measurements.reduce((a, b) => a + b, 0) / measurements.length
    };
}

/**
 * Sets network throttling for the page using Chrome DevTools Protocol.
 *
 * @param page - Playwright Page object
 * @param preset - Network preset name from NETWORK_PRESETS (e.g., 'Fast4G')
 *
 * @example
 * await setNetworkThrottling(page, 'Fast4G');
 */
export async function setNetworkThrottling(page: Page, preset: NetworkPreset): Promise<void> {
    const client = await page.context().newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', NETWORK_PRESETS[preset]);
}

// Helper function to check if element is in viewport (like IntersectionObserver).
export const isInViewport = async ({
    element,
    viewport
}: {
    element: Locator;
    viewport: Locator;
}) => {
    const count = await element.count();
    if (count === 0 || (await element.isVisible()) === false) {
        return false;
    }
    const viewportRect = await viewport.evaluate((el: Element) => el.getBoundingClientRect());
    return await element.evaluate((el: Element, viewportRect: DOMRect) => {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= viewportRect.top &&
            rect.left >= viewportRect.left &&
            rect.bottom <= viewportRect.bottom &&
            rect.right <= viewportRect.right
        );
    }, viewportRect);
};
