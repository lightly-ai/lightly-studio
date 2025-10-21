import { test, expect } from '../utils';
import { cocoDataset } from '../fixtures';

test('user can navigate with keyboard keys within selected label', async ({
    page,
    samplesPage
}) => {
    // samplesPage fixture automatically navigates and loads samples

    // Expect to see the baseball glove label in the labels menu
    const labelName = cocoDataset.labels.baseballGlove.name;
    await expect(samplesPage.getLabelsMenuItem(labelName)).toBeVisible();

    // Filter by baseball glove label
    await samplesPage.clickLabel(labelName);

    // Wait for sample list to load
    await expect(samplesPage.getSamples().first()).toBeVisible();

    // Expect to have all samples with this label
    const expectedTotalLabelCount = cocoDataset.labels.baseballGlove.sampleCount;
    await expect(samplesPage.getSamples()).toHaveCount(expectedTotalLabelCount);

    // Double-click on the second sample link
    await samplesPage.getSampleByIndex(1).dblclick();
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 2 of ${expectedTotalLabelCount}`)).toBeVisible();

    // Navigate to the first sample using keyboard
    await expect(page.getByRole('button', { name: 'Previous sample' })).toBeVisible();
    await page.keyboard.press('ArrowLeft');
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 1 of ${expectedTotalLabelCount}`)).toBeVisible();

    // Navigate to the second sample using keyboard
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 2 of ${expectedTotalLabelCount}`)).toBeVisible();

    // Navigate to the third sample using keyboard
    await expect(page.getByRole('button', { name: 'Next sample' })).toBeVisible();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
    await expect(page.getByText(`Sample 3 of ${expectedTotalLabelCount}`)).toBeVisible();
});
