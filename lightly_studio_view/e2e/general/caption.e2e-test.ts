import { test, expect } from '../utils';

test.describe('captions-page-flow', () => {
    test('Add a caption in sample details', async ({ samplesPage, sampleDetailsPage }) => {
        // Double-click on the first sample to navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Initially there are no captions
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(0);

        // Start edit mode and add a caption
        await sampleDetailsPage.clickEditButton();
        await sampleDetailsPage.addCaption();
        await sampleDetailsPage.updateNthCaption(0, 'caption');

        // Check a caption was added
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(1);
    });

    test('Add and edit captions in caption page', async ({ captionsPage }) => {
        // There should be just one sample
        expect(await captionsPage.getGridItemCount()).toEqual(1);

        // There should be just one caption
        expect(await captionsPage.getCaptionCount()).toEqual(1);
        expect(await captionsPage.getNthCaptionText(0)).toEqual('caption');

        // Toggle the edit mode
        await captionsPage.clickEditButton();

        // Add a caption
        await captionsPage.addCaption(0);
        await captionsPage.updateNthCaption(1, 'caption in caption page');
        expect(await captionsPage.getGridItemCount()).toEqual(1);
        expect(await captionsPage.getCaptionCount()).toEqual(2);
        expect(await captionsPage.getNthCaptionInput(1)).toEqual('caption in caption page');
    });

    test('Delete a caption in caption page', async ({ captionsPage }) => {
        // Start edit mode and delete the last caption
        await captionsPage.clickEditButton();
        await captionsPage.deleteNthCaption(1);

        // Check the remaining caption
        expect(await captionsPage.getCaptionCount()).toEqual(1);
        expect(await captionsPage.getNthCaptionInput(0)).toEqual('caption');

        // Deleting the last caption also hides the sample
        await captionsPage.deleteNthCaption(0);
        expect(await captionsPage.getCaptionCount()).toEqual(0);
        expect(await captionsPage.getGridItemCount()).toEqual(0);
    });
});
