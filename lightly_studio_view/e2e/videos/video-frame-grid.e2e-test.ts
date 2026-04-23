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

    test('Tags can be created from the side panel for selected frames', async ({
        videoFramesPage
    }) => {
        const tagName = `frame_tag_${Date.now()}`;

        await videoFramesPage.getVideoFrameByIndex(0).click();
        await videoFramesPage.getVideoFrameByIndex(1).click();
        expect(await videoFramesPage.getNumSelectedSamples()).toBe(2);

        await videoFramesPage.createTag(tagName);
        await videoFramesPage.pressTag(tagName);

        await expect(videoFramesPage.getVideoFrames()).toHaveCount(2, {
            timeout: 10000
        });
    });
});

test('We can see clicked element when navigating back from details', async ({
    page,
    videoFramesPage
}) => {
    await page.setViewportSize({ width: 800, height: 400 });

    const viewport = page.getByTestId('video-frames-grid');
    await expect(viewport).toBeVisible();

    expect(await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(0), viewport })).toBe(
        true
    );
    expect(
        await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(30), viewport })
    ).toBe(false);

    await videoFramesPage.getVideoFrameByIndex(30).scrollIntoViewIfNeeded();

    expect(await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(0), viewport })).toBe(
        false
    );
    expect(
        await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(30), viewport })
    ).toBe(true);

    await videoFramesPage.getVideoFrameByIndex(30).dblclick();

    await expect(page.getByText('Video frame details')).toBeVisible();

    await page.goBack();

    await expect(viewport).toBeVisible();

    expect(
        await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(30), viewport })
    ).toBe(true);
    expect(await isInViewport({ element: videoFramesPage.getVideoFrameByIndex(0), viewport })).toBe(
        false
    );
});
