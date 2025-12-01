import { test, expect } from '../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate with prev/next buttons within selected label', async ({
    page,
    samplesPage
}) => {
    // samplesPage fixture automatically navigates and loads samples

    // Filter by baseball glove label
    await samplesPage.clickLabel(cocoDataset.labels.baseballGlove.name);

    // Expect to have all samples with this label
    const expectedTotalLabelCount = cocoDataset.labels.baseballGlove.sampleCount;
    await expect(samplesPage.getSamples()).toHaveCount(expectedTotalLabelCount);

    // Double-click on the second sample
    // update get sample by index
    await samplesPage.doubleClickNthSample(1);
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 2 of ${expectedTotalLabelCount}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

    // Navigate to the first sample
    await page.getByRole('button', { name: 'Previous sample' }).click();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 1 of ${expectedTotalLabelCount}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Previous sample' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

    // Navigate to the second sample
    await page.getByRole('button', { name: 'Next sample' }).click();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 2 of ${expectedTotalLabelCount}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();

    // Navigate to the third sample
    await page.getByRole('button', { name: 'Next sample' }).click();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 3 of ${expectedTotalLabelCount}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next sample' })).not.toBeVisible();
});
