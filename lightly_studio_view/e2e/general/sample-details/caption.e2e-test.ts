import { test, expect } from '../../utils';

test.describe('caption-flow1', () => {
    test('Add and edit captions in sample details', async ({ samplesPage, sampleDetailsPage }) => {
        // Double-click on the first sample to navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Initially there are no captions
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(0);

        // Start edit mode and add a caption
        await sampleDetailsPage.clickEditButton();
        await sampleDetailsPage.addCaption();
        await sampleDetailsPage.updateNthCaption(0, 'caption');

        // Check the first caption
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(1);
        expect(await sampleDetailsPage.getNthCaptionInput(0)).toEqual('caption');

        // Add a second caption
        await sampleDetailsPage.addCaption();
        await sampleDetailsPage.updateNthCaption(1, 'another caption');

        // Check the second caption
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(2);
        expect(await sampleDetailsPage.getNthCaptionInput(1)).toEqual('another caption');
    });

    test('Delete a caption in sample details', async ({ samplesPage, sampleDetailsPage }) => {
        // Navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Start edit mode and delete the first caption
        await sampleDetailsPage.clickEditButton();
        await sampleDetailsPage.deleteNthCaption(0);

        // Check the remaining caption
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(1);
        expect(await sampleDetailsPage.getNthCaptionInput(0)).toEqual('another caption');
    });
});
