import { expect, Page, test as base } from '@playwright/test';
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

export { expect } from '@playwright/test';
