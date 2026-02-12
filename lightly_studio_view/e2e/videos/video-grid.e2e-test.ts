import { test, expect, pressButton } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test.describe('videos-page-flow', () => {
    test('scroll to the bottom of the grid container', async ({ page, videosPage }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);
        const gridContainer = page.getByTestId('video-grid');
        // Wait for API response when scrolling triggers loadMore
        const responsePromise = page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/api/collections/') &&
                response.url().includes('/video/') &&
                response.status() === 200
        );

        // Scroll to bottom - use a method that triggers scroll events
        await gridContainer.evaluate((el) => {
            el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
        });

        // Wait for the API response
        await responsePromise;

        // Wait a bit for the grid to update
        await page.waitForTimeout(100);

        // Check that all videos are loaded
        await expect(videosPage.getVideos()).toHaveCount(youtubeVisVideosDataset.totalSamples, {
            timeout: 10000
        });
    });

    test('filter videos by label', async ({ videosPage }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);
        await videosPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);
        expect(await videosPage.getVideos().count()).toBe(
            youtubeVisVideosDataset.labels.airplane.sampleCount
        );
        await videosPage.clickLabel(youtubeVisVideosDataset.labels.bird.name);
        expect(await videosPage.getVideos().count()).toBe(
            youtubeVisVideosDataset.labels.airplane.sampleCount +
                youtubeVisVideosDataset.labels.bird.sampleCount
        );
    });

    // TODO (Kondrat 02/25): Test is disabled due to flakiness, needs to be fixed in the future
    test.skip('go to video details', async ({ page, videosPage }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);

        expect(videosPage.getVideoByName(youtubeVisVideosDataset.airplaneVideo.name)).toBeVisible();
        await videosPage.getVideoByName(youtubeVisVideosDataset.airplaneVideo.name).dblclick();

        // Wait for video details page to load
        await expect(page.getByTestId('video-file-name')).toBeVisible({
            timeout: 10000
        });

        // Verify video details are displayed
        expect(await page.getByTestId('video-file-name').textContent()).toBe(
            youtubeVisVideosDataset.airplaneVideo.name
        );
        expect(await page.getByTestId('video-width').textContent()).toBe(
            `${youtubeVisVideosDataset.airplaneVideo.width}px`
        );
        expect(await page.getByTestId('video-height').textContent()).toBe(
            `${youtubeVisVideosDataset.airplaneVideo.height}px`
        );
    });

    test('navigate from video details to frame details', async ({ page, videosPage }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);

        expect(videosPage.getVideoByName(youtubeVisVideosDataset.airplaneVideo.name)).toBeVisible();
        await videosPage.getVideoByName(youtubeVisVideosDataset.airplaneVideo.name).dblclick();

        // Wait for video details page to load
        await expect(page.getByTestId('video-file-name')).toBeVisible({
            timeout: 10000
        });
        await pressButton(page, 'view-frame-button');
        // Wait for frame details page to load
        await expect(page.getByTestId('frame-details-video-file-path')).toBeVisible({
            timeout: 10000
        });
        // Verify frame details are displayed
        expect(await page.getByTestId('frame-details-video-file-path').textContent()).toContain(
            youtubeVisVideosDataset.airplaneVideo.name
        );
    });

    test('user can navigate prev/next with buttons or keys in video details page', async ({
        page,
        videosPage
    }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);

        await videosPage.getVideoByIndex(1).dblclick();

        // Wait for video details page to load
        await expect(page.getByTestId('video-file-name')).toBeVisible({
            timeout: 10000
        });
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 2 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();
        await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

        // Navigate to the first sample
        await page.getByRole('button', { name: 'Previous sample' }).click();
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 1 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();
        await expect(page.getByRole('button', { name: 'Previous sample' })).not.toBeVisible();
        await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

        // Navigate to the second sample
        await page.getByRole('button', { name: 'Next sample' }).click();
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 2 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();
        await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

        // Navigate to the third sample
        await page.getByRole('button', { name: 'Next sample' }).click();
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 3 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();

        // Navigate with keys
        await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
        await page.keyboard.press('ArrowLeft');
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 2 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();

        await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();
        await page.keyboard.press('ArrowRight');
        await expect(page.getByTestId('details-breadcrumb')).toBeVisible();
        await expect(
            page.getByText(`Video 3 of ${youtubeVisVideosDataset.totalFrames}`)
        ).toBeVisible();
    });

    test('add new tag', async ({ videosPage }) => {
        const tagName = `tag_${Date.now()}`;
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);
        // Select 2 samples
        await videosPage.getVideoByIndex(0).click();
        await videosPage.getVideoByIndex(1).click();
        expect(await videosPage.getNumSelectedSamples()).toBe(2);
        await videosPage.createTag(tagName);
        // Wait for the tag to appear in the tags menu
        await expect(videosPage.getTagsMenuItem(tagName)).toBeVisible({
            timeout: 10000
        });
        // Filter by the newly created tag
        await videosPage.pressTag(tagName);
        // Wait for the filtered results to load
        await expect(videosPage.getVideos()).toHaveCount(2, {
            timeout: 10000
        });
    });
});
