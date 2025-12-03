import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

// test('todo', async ({ page, samplesPage, sampleDetailsPage }) => {
test('todo', async ({ samplesPage, sampleDetailsPage }) => {
    // Double-click on the first sample to navigate to sample details
    await samplesPage.doubleClickFirstSample();

    // Wait for sample details to load
    await sampleDetailsPage.pageIsReady();

    expect(await sampleDetailsPage.getCaptionCount()).toEqual(0);

    await sampleDetailsPage.clickEditButton();
    await sampleDetailsPage.addCaption();
    await sampleDetailsPage.updateNthCaption(0, "caption0");

    expect(await sampleDetailsPage.getCaptionCount()).toEqual(1);

    // await sampleDetailsPage.addCaption();

    // expect(await sampleDetailsPage.getCaptionCount()).toEqual(2);

});
