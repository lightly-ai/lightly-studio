import { test, expect } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test.describe('video-frames-page-flow', () => {
    test('scroll in the grid container', async ({ page, videoFramesPage }) => {
        expect(await videoFramesPage.getVideoFrames().count()).toBe(
            youtubeVisVideosDataset.defaultPageSize
        );

        // Check scroll works
        const gridContainer = page.getByTestId('video-frames-grid');
        await gridContainer.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
        });

        // Check that more video frames are loaded
        await expect(videoFramesPage.getVideoFrames()).toHaveCount(
            youtubeVisVideosDataset.defaultPageSize * 2
        );
    });

    test('filter frames by label', async ({ page, videoFramesPage }) => {
        expect(await videoFramesPage.getVideoFrames().count()).toBe(
            youtubeVisVideosDataset.defaultPageSize
        );
        await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);

        // Scroll to load all frames with the label
        const gridContainer = page.getByTestId('video-frames-grid');
        await gridContainer.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
        });
        await expect(videoFramesPage.getVideoFrames()).toHaveCount(
            youtubeVisVideosDataset.labels.airplane.frameCount
        );

        await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.elephant.name);
        // Scroll twice to load all frames with both labels
        await gridContainer.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
        });
        await expect(videoFramesPage.getVideoFrames()).toHaveCount(
            youtubeVisVideosDataset.labels.airplane.frameCount +
                youtubeVisVideosDataset.labels.elephant.frameCount
        );
    });
});
