import { test, expect } from '../utils';

test.describe('caption-flow1', () => {
    test('Add a caption in sample details', async ({
        samplesPage,
        sampleDetailsPage,
        captionUtils
    }) => {
        // Double-click on the first sample to navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Initially there are no captions
        expect(await captionUtils.getCaptionCount()).toEqual(0);

        // Start edit mode and add a caption
        await sampleDetailsPage.clickEditButton();
        await captionUtils.addCaption();
        await captionUtils.updateNthCaption(0, 'caption');

        // Check a caption was added
        expect(await captionUtils.getCaptionCount()).toEqual(1);
    });

    test('Add and edit captions in caption page', async ({ captionsPage, captionUtils }) => {
        // There should be just one sample
        expect(await captionsPage.getGridItemCount()).toEqual(1);

        // There should be just one caption
        expect(await captionUtils.getCaptionCount()).toEqual(1);
        expect(await captionUtils.getNthCaptionText(0)).toEqual('caption');

        // Toggle the edit mode
        await captionsPage.clickEditButton();

        // Add a caption
        await captionUtils.addCaption(0);
        await captionUtils.updateNthCaption(1, 'caption in caption page');
        expect(await captionsPage.getGridItemCount()).toEqual(1);
        expect(await captionUtils.getCaptionCount()).toEqual(2);
        expect(await captionUtils.getNthCaptionInput(1)).toEqual('caption in caption page');
    });

    test('Delete a caption in caption page', async ({ captionsPage, captionUtils }) => {
        // Start edit mode and delete the last caption
        await captionsPage.clickEditButton();
        await captionUtils.deleteNthCaption(1);

        // Check the remaining caption
        expect(await captionUtils.getCaptionCount()).toEqual(1);
        expect(await captionUtils.getNthCaptionInput(0)).toEqual('caption');

        // Deleting the last caption also hides the sample
        await captionUtils.deleteNthCaption(0);
        expect(await captionUtils.getCaptionCount()).toEqual(0);
        expect(await captionsPage.getGridItemCount()).toEqual(0);
    });
});
