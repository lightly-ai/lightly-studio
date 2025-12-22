import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate to sample details', async ({ page, samplesPage, sampleDetailsPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Expect first page of samples to be loaded (default page size from COCO collection)
    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(cocoDataset.defaultPageSize);

    // Wait for labels menu to load
    await expect(page.getByTestId('labels-menu-item').first()).toBeVisible();

    // Expect to have all labels from the COCO collection
    const labelsCount = await page.getByTestId('labels-menu-item').count();
    expect(labelsCount).toBe(cocoDataset.totalLabels);

    // Double-click on the first sample to navigate to sample details
    await samplesPage.doubleClickFirstSample();

    // Wait for sample details to load
    await sampleDetailsPage.pageIsReady();
});
