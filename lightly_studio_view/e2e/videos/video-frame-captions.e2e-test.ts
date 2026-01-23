import { test, expect } from '../utils';

// This tests are dependent of each other.
test.describe('video-frames-page-flow-captions', () => {
    test('add captions in video frame details', async ({
        videoFramesPage,
        videoFrameDetailsPage
    }) => {
        await videoFramesPage.doubleClickFirstVideoFrame();

        await videoFrameDetailsPage.pageIsReady();

        expect(await videoFrameDetailsPage.getCaptionCount()).toEqual(0);

        // Start edit mode
        await videoFrameDetailsPage.clickEditButton();
        await videoFrameDetailsPage.addCaption();
        await videoFrameDetailsPage.updateNthCaption(0, 'caption');

        // Check the first caption
        expect(await videoFrameDetailsPage.getCaptionCount()).toEqual(1);
        expect(await videoFrameDetailsPage.getNthCaptionInput(0)).toEqual('caption');

        // Add a second caption
        await videoFrameDetailsPage.addCaption();
        await videoFrameDetailsPage.updateNthCaption(1, 'caption 1');

        // Check the second caption
        expect(await videoFrameDetailsPage.getCaptionCount()).toEqual(2);
        expect(await videoFrameDetailsPage.getNthCaptionInput(1)).toEqual('caption 1');
    });

    test('delete a caption in video frame details', async ({
        videoFramesPage,
        videoFrameDetailsPage
    }) => {
        await videoFramesPage.doubleClickFirstVideoFrame();
        await videoFrameDetailsPage.pageIsReady();

        // Start edit mode
        await videoFrameDetailsPage.clickEditButton();

        // Delete first caption
        await videoFrameDetailsPage.deleteNthCaption(0);

        // Check the remaining caption
        expect(await videoFrameDetailsPage.getCaptionCount()).toEqual(1);
        expect(await videoFrameDetailsPage.getNthCaptionInput(0)).toEqual('caption 1');
    });

    test('add and edit captions in caption page', async ({ captionsVideoFramePage }) => {
        // There should be just one caption
        expect(await captionsVideoFramePage.getCaptionCount()).toEqual(1);
        expect(await captionsVideoFramePage.getNthCaptionText(0)).toEqual('caption 1');

        // Toggle the edit mode
        await captionsVideoFramePage.clickEditButton();

        // Add a caption
        await captionsVideoFramePage.addCaption(0);
        await captionsVideoFramePage.updateNthCaption(1, 'caption in caption page');
        expect(await captionsVideoFramePage.getGridItemCount()).toEqual(1);
        expect(await captionsVideoFramePage.getCaptionCount()).toEqual(2);
        expect(await captionsVideoFramePage.getVideoFrameImageCount()).toEqual(1);
        expect(await captionsVideoFramePage.getNthCaptionInput(1)).toEqual(
            'caption in caption page'
        );
    });

    test('delete a caption in caption page', async ({ captionsVideoFramePage }) => {
        // Start edit mode
        await captionsVideoFramePage.clickEditButton();

        // Delete last caption
        await captionsVideoFramePage.deleteNthCaption(1);

        // Check the remaining caption
        expect(await captionsVideoFramePage.getCaptionCount()).toEqual(1);
        expect(await captionsVideoFramePage.getNthCaptionInput(0)).toEqual('caption 1');

        // Deleting the last caption also hides the sample
        await captionsVideoFramePage.deleteNthCaption(0);
        expect(await captionsVideoFramePage.getCaptionCount()).toEqual(0);
        expect(await captionsVideoFramePage.getGridItemCount()).toEqual(0);
        expect(await captionsVideoFramePage.getVideoFrameImageCount()).toEqual(0);
    });
});
