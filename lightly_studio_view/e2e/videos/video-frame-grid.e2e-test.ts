import { test, expect, isInViewport, scrollDownToGridItem } from '../utils';
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

        const nextPage = page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/frame') &&
                new URL(response.url()).searchParams.get('cursor') ===
                    String(youtubeVisVideosDataset.defaultPageSize) &&
                response.status() === 200
        );
        await page.getByTestId('video-frames-grid').evaluate((el) => {
            el.scrollTop = el.scrollHeight;
        });
        await nextPage;
        // Loaded frames outside the overscan window are intentionally absent from the DOM.
        await expect(
            videoFramesPage.getVideoFrameByIndex(youtubeVisVideosDataset.defaultPageSize)
        ).toBeAttached();
    });

    test('filter frames by label', async ({ page, videoFramesPage }) => {
        expect(await videoFramesPage.getVideoFrames().count()).toBe(
            youtubeVisVideosDataset.defaultPageSize
        );
        await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);

        await expect(
            page.getByText(
                new RegExp(
                    `^Showing ${youtubeVisVideosDataset.labels.airplane.frameCount} of [\\d,]+ video frames$`
                )
            )
        ).toBeVisible();
        await expect(videoFramesPage.getVideoFrames().first()).toBeVisible();

        await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.elephant.name);
        await expect(
            page.getByText(
                new RegExp(
                    `^Showing ${youtubeVisVideosDataset.labels.airplane.frameCount + youtubeVisVideosDataset.labels.elephant.frameCount} of [\\d,]+ video frames$`
                )
            )
        ).toBeVisible();
        await expect(videoFramesPage.getVideoFrames().first()).toBeVisible();
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

    await scrollDownToGridItem(viewport, videoFramesPage.getVideoFrameByIndex(30));

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
