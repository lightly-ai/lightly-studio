import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate to sample details', async ({ samplesPage, sampleDetailsPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Expect first page of samples to be loaded (default page size from COCO collection)
    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(cocoDataset.defaultPageSize);

    // Expect to have all labels from the COCO collection
    await samplesPage.annotationTree.groupByClass();
    await expect(samplesPage.annotationTree.getClassGroupNames()).toHaveCount(
        cocoDataset.totalLabels
    );

    // Double-click on the first sample to navigate to sample details
    await samplesPage.doubleClickFirstSample();

    // Wait for sample details to load
    await sampleDetailsPage.pageIsReady();
});
