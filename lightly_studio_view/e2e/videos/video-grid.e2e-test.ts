import { test, expect } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test.describe('videos-page-flow', () => {
    test('scroll to the bottom of the grid container', async ({ page, videosPage }) => {
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.defaultPageSize);

        // Scroll to the bottom of the grid container
        const gridContainer = page.getByTestId('video-grid');
        await gridContainer.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
        });

        // Check that all videos are loaded
        await expect(videosPage.getVideos()).toHaveCount(youtubeVisVideosDataset.totalSamples);
    });

    test('filter videos by label', async ({ page, videosPage }) => {
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
});
