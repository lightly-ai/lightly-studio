import { test, expect } from '../utils';

test.describe('captions-page-flow', () => {
    test.skip('Add a caption in sample details', async ({ samplesPage, sampleDetailsPage }) => {
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

    test.skip('Add and edit captions in caption page', async ({ captionsPage }) => {
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
        const page = captionsPage.page;

        // Capture browser console
        page.on('console', (msg) => {
            if (msg.text().includes('[refresh]')) {
                console.log('BROWSER:', msg.text());
            }
        });

        // Start edit mode and delete the last caption
        await captionsPage.clickEditButton();
        const initialCount = await captionsPage.getCaptionCount();
        console.log('Initial caption count:', initialCount);
        await captionsPage.deleteNthCaption(initialCount - 1);
        expect(await captionsPage.getCaptionCount()).toEqual(initialCount - 1);

        // Undo
        await captionsPage.undoLastCaptionDelete();
        expect(await captionsPage.getCaptionCount()).toEqual(initialCount);
    });
});
