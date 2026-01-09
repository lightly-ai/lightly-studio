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

        // Wait for more videos to load by checking if the count increases
        await page.waitForFunction(
            (expectedCount) => {
                return document.querySelectorAll('[data-testid="video-grid-item"]').length >= expectedCount;
            },
            youtubeVisVideosDataset.totalSamples,
            { timeout: 10000 }
        );

        // Wait for the last video to be visible (indicating all videos have loaded)
        await expect(videosPage.getVideos().last()).toBeVisible({ timeout: 10000 });

        // Check the total number of videos after scrolling
        expect(await videosPage.getVideos().count()).toBe(youtubeVisVideosDataset.totalSamples);
    });
});
