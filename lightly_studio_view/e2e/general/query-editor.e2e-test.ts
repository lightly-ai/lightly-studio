import { test, expect } from '../utils';
import { cocoDataset } from './fixtures';

const QUERY = 'segmentation_mask(class_name = "airplane")';

test.describe('query editor', () => {
    test('apply query and verify filtered grid', async ({ samplesPage, page }) => {
        await page.getByTestId('query-filter-add-button').click();
        await expect(page.getByRole('heading', { name: 'Query Filter' })).toBeVisible();

        // On first open: The apply button should be enabled.
        await expect(page.getByTestId('query-editor-apply-button')).toBeEnabled();

        // Type the query into Monaco
        // Click the editor content area to focus Monaco, then select-all and type
        await page.locator('.monaco-editor .view-lines').first().click();
        await page.keyboard.press('ControlOrMeta+a');
        await page.keyboard.type(QUERY);

        // Click Apply and wait for the filtered image list response
        const applyButton = page.getByTestId('query-editor-apply-button');
        const refetchPromise = page.waitForResponse(
            (r) => r.url().includes('/images/list') && r.status() === 200
        );
        await applyButton.click();
        await refetchPromise;

        // Verify the grid shows only airplane samples
        await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.labels.airplane.sampleCount);

        // Apply button should be disabled (draft matches applied value)
        await expect(applyButton).toBeDisabled();

        // Filter chip should be visible
        await expect(page.getByTestId('query-filter-chip')).toBeVisible();
    });
});
