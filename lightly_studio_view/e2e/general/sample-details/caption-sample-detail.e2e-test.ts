import { test, expect } from '../../utils';

test.describe('sample-details-page-caption-flow', () => {
    test('Add and edit captions in sample details', async ({
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

        // Check the first caption
        expect(await captionUtils.getCaptionCount()).toEqual(1);
        expect(await captionUtils.getNthCaptionInput(0)).toEqual('caption');

        // Add a second caption
        await captionUtils.addCaption();
        await captionUtils.updateNthCaption(1, 'another caption');

        // Check the second caption
        expect(await captionUtils.getCaptionCount()).toEqual(2);
        expect(await captionUtils.getNthCaptionInput(1)).toEqual('another caption');
    });

    test('Delete a caption in sample details', async ({
        samplesPage,
        sampleDetailsPage,
        captionUtils
    }) => {
        // Navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Start edit mode and delete the first caption
        await sampleDetailsPage.clickEditButton();
        await captionUtils.deleteNthCaption(0);

        // Check the remaining caption
        expect(await captionUtils.getCaptionCount()).toEqual(1);
        expect(await captionUtils.getNthCaptionInput(0)).toEqual('another caption');
    });

    test('Clean up', async ({ samplesPage, sampleDetailsPage, captionUtils }) => {
        // Navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Start edit mode and delete the remaining caption
        await sampleDetailsPage.clickEditButton();
        await captionUtils.deleteNthCaption(0);

        // Check that there are no captions left
        expect(await captionUtils.getCaptionCount()).toEqual(0);
    });
});
