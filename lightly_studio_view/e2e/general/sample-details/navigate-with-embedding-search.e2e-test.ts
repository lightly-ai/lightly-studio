import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate with prev/next buttons within search', async ({ page, samplesPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Search for samples with "bear" - this searches across all samples in the collection
    const searchTerm = cocoDataset.labels.bear.name;
    await samplesPage.textSearch(searchTerm);

    // Double-click on the first sample
    await samplesPage.doubleClickFirstSample();

    // Check what sample is displayed - search shows results from all samples in collection
    const totalSamples = cocoDataset.totalSamples;
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 1 of ${totalSamples}`)).toBeVisible({
        timeout: 10000
    });

    // Check that next button is visible
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();
    // Check that previous button is not visible
    await expect(page.getByRole('button', { name: 'Previous sample' })).not.toBeVisible();

    // Navigate to the second sample
    await page.getByRole('button', { name: 'Next sample' }).click();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 2 of ${totalSamples}`)).toBeVisible({
        timeout: 10000
    });
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

    // Navigate to the third sample
    await page.getByRole('button', { name: 'Next sample' }).click();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 3 of ${totalSamples}`)).toBeVisible({
        timeout: 10000
    });
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();
});
