import { test, expect, isInViewport } from '../utils';
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

test('Scroll position is restored when navigating back from details', async ({
    page,
    videoFramesPage
}) => {
    await page.setViewportSize({ width: 800, height: 400 });

    const gridContainer = page.getByTestId('video-frames-grid');
    await expect(gridContainer).toBeVisible();

    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(0))).toBe(true);
    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(30))).toBe(false);

    await gridContainer.evaluate((element) => {
        element.scrollBy({ top: 300, behavior: 'instant' });
    });

    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(0))).toBe(false);
    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(30))).toBe(true);

    await videoFramesPage.getVideoFrameByIndex(30).dblclick();

    await expect(page.getByText('Video frame details')).toBeVisible();

    await page.goBack();

    await expect(gridContainer).toBeVisible();

    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(30))).toBe(true);
    expect(await isInViewport(videoFramesPage.getVideoFrameByIndex(0))).toBe(false);
});
