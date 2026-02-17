import { test, expect } from '../utils';

test.describe('video-frames-details', () => {
    test('Go to video details view', async ({ page, videoFramesPage, videoFrameDetailsPage }) => {
        await videoFramesPage.doubleClickNthVideoFrame(3);

        await videoFrameDetailsPage.pageIsReady();

        const frameNumberText = await videoFrameDetailsPage.getFrameNumber();

        await videoFramesPage.page.getByTestId('view-video-button').click();

        const currentFrameNumber = page.getByTestId('current-frame-number');

        await expect(currentFrameNumber).toBeVisible({ timeout: 10000 });

        expect(Number(await currentFrameNumber.textContent())).toBe(Number(frameNumberText));
    });
});
