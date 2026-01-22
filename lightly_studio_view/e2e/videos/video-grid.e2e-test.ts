import { test, expect } from '../utils';
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

    // TODO(Kondrat, 01/2026): The test is flakey, needs investigation.
    test.skip('add new tag', async ({ videosPage }) => {
        const tagName = `tag_${Date.now()}`;
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);
        // Select 2 samples
        await videosPage.getVideoByIndex(0).click();
        await videosPage.getVideoByIndex(1).click();
        expect(await videosPage.getNumSelectedSamples()).toBe(2);
        await videosPage.createTag(tagName);
        expect(videosPage.getTagsMenuItem(tagName)).toBeDefined();
        // Filter by the newly created tag
        await videosPage.pressTag(tagName);
        expect(await videosPage.getVideos().count()).toBe(2);
    });
});
