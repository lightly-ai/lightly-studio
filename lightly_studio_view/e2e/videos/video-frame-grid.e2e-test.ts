import { test, expect } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test.describe('video-frames-page-flow', () => {
    test('Shift+click adds the full range in frame grid', async ({ videoFramesPage }) => {
        await videoFramesPage.getVideoFrameByIndex(1).click();
        expect(await videoFramesPage.getNumSelectedSamples()).toBe(1);

        await videoFramesPage.getVideoFrameByIndex(7).click({
            modifiers: ['Shift']
        });
        expect(await videoFramesPage.getNumSelectedSamples()).toBe(7);
    });

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
            youtubeVisVideosDataset.defaultPageSize * 2,
            {
                timeout: 10000
            }
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
