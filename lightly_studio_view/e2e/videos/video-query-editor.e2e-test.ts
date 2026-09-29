import type { Page, Response } from '@playwright/test';
import { test, expect } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

// The annotations are on the video frames, not on the videos.
const QUERY = 'segmentation_mask(class_name = "airplane")';

function waitForVideoListResponse(page: Page): Promise<Response> {
    return page.waitForResponse(
        (r) =>
            r.request().method() === 'POST' &&
            new URL(r.url()).pathname.endsWith('/video/') &&
            r.status() === 200
    );
}

/** Select-all in Monaco, type a query, click Apply, and wait for the grid to update. */
async function typeAndApply(page: Page, query: string): Promise<void> {
    await page.locator('.monaco-editor .view-lines').first().click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type(query);

    const refetchPromise = waitForVideoListResponse(page);
    await page.getByTestId('query-editor-apply-button').click();
    await refetchPromise;
}

test.describe('video query editor', () => {
    test('apply query and verify filtered grid', async ({ videosPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await expect(page.getByRole('heading', { name: 'Query Filter' })).toBeVisible();
        await expect(page.getByText('Video fields:')).toBeVisible();

        await typeAndApply(page, QUERY);

        await expect(videosPage.getVideos()).toHaveCount(
            youtubeVisVideosDataset.labels.airplane.sampleCount
        );
        await expect(page.getByTestId('query-editor-apply-button')).toBeDisabled();
        await expect(page.getByTestId('query-filter-chip')).toBeVisible();
    });

    test('video field query filters the grid', async ({ videosPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();

        await typeAndApply(page, `file_name = "${youtubeVisVideosDataset.airplaneVideo.name}"`);

        await expect(videosPage.getVideos()).toHaveCount(1);
    });

    test('toggling filter chip disables and re-enables query', async ({ videosPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(page, QUERY);
        await page.getByTestId('query-editor-close-button').click();

        const disableRefetch = waitForVideoListResponse(page);
        await page.getByRole('checkbox', { name: 'Disable query filter' }).click();
        await disableRefetch;
        // Infinite scroll can load more pages, so check for at least one full page.
        await expect
            .poll(() => videosPage.getVideos().count())
            .toBeGreaterThanOrEqual(youtubeVisVideosDataset.defaultPageSize);

        const enableRefetch = waitForVideoListResponse(page);
        await page.getByRole('checkbox', { name: 'Enable query filter' }).click();
        await enableRefetch;
        await expect(videosPage.getVideos()).toHaveCount(
            youtubeVisVideosDataset.labels.airplane.sampleCount
        );
    });
});
