import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate to sample details', async ({ page, samplesPage, sampleDetailsPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Infinite scroll may preload additional pages, so only require one full page.
    await expect
        .poll(() => samplesPage.getSamples().count())
        .toBeGreaterThanOrEqual(cocoDataset.defaultPageSize);

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
