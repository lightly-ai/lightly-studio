import { expect, test } from '../utils';
import { cocoDataset } from './fixtures';

test('select all annotations with label filter via keyboard shortcut', async ({
    page,
    annotationsPage
}) => {
    // Apply a label filter to reduce the visible annotations
    await annotationsPage.clickLabel(cocoDataset.labels.dog.name);
    const filteredCount = await annotationsPage.getAnnotations().count();
    expect(filteredCount).toBe(cocoDataset.labels.dog.annotationCount);

    // Press Cmd+A / Ctrl+A to select all filtered annotations
    await page.click('body');
    const sampleIdsResponse = page.waitForResponse(
        (response) =>
            response.url().includes('/annotations/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await sampleIdsResponse;

    // All filtered annotations should be selected
    expect(await annotationsPage.getSelectedItemsCount()).toBe(
        cocoDataset.labels.dog.annotationCount
    );

    // Wait for the success toast to disappear before proceeding
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(0, { timeout: 5000 });

    // Clear the selection
    await page.getByTestId('clear-selection-button').click();

    // Wait for the selection pill to disappear
    await expect(page.getByTestId('clear-selection-button')).toBeHidden();

    // Remove the label filter and select all again
    await annotationsPage.clickLabel(cocoDataset.labels.dog.name);
    await expect(annotationsPage.getAnnotations().first()).toBeVisible({ timeout: 10000 });

    await page.click('body');
    const allSampleIdsResponse = page.waitForResponse(
        (response) =>
            response.url().includes('/annotations/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await allSampleIdsResponse;

    // All annotations should be selected. Since we don't track total annotations in the fixture,
    // assert the selection pill shows a count greater than the filtered count.
    const selectionText = await page.getByText(/\d+ selected/).textContent();
    const selectedCount = parseInt(selectionText.split(' ')[0], 10);
    expect(selectedCount).toBeGreaterThan(cocoDataset.labels.dog.annotationCount);
});
