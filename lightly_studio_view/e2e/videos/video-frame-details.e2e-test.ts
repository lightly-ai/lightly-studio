import { test, expect } from '../utils';

test.describe('video-frames-details', () => {
    test('Go to video details view', async ({ page, videoFramesPage, videoFrameDetailsPage }) => {
        await videoFramesPage.doubleClickNthVideoFrame(3);

        await videoFrameDetailsPage.pageIsReady();

        const frameNumberText = await videoFrameDetailsPage.getFrameNumber();
        const frameTimestampText = await videoFrameDetailsPage.getFrameTimestamp();
        console.log(frameNumberText, frameTimestampText);
        await videoFramesPage.page.getByTestId('view-video-button').click();

        const currentFrameNumber = page.getByTestId('current-frame-number');
        const currentFrameTimestamp = page.getByTestId('current-frame-timestamp');

        await expect(currentFrameNumber).toBeVisible({ timeout: 10000 });
        await expect(currentFrameTimestamp).toBeVisible({ timeout: 10000 });
        console.log(await currentFrameNumber.textContent(), currentFrameTimestamp.textContent());
        expect(Number(await currentFrameNumber.textContent())).toBe(Number(frameNumberText));
    });
});
