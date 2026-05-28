import { expect, test } from '../utils';
import { cocoDataset } from './fixtures';

test('select all images with label filter via keyboard shortcut', async ({ page, samplesPage }) => {
    // Apply a label filter to reduce the visible samples
    await samplesPage.clickLabel(cocoDataset.labels.dog.name);
    const filteredCount = await samplesPage.getSamples().count();
    expect(filteredCount).toBe(cocoDataset.labels.dog.sampleCount);

    // Press Cmd+A / Ctrl+A to select all filtered samples
    await page.click('body');
    const sampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/images/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await sampleIdsResponse;

    // All filtered samples should be selected
    expect(await samplesPage.getNumSelectedSamples()).toBe(cocoDataset.labels.dog.sampleCount);

    // Wait for the success toast to disappear before proceeding
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(0, { timeout: 5000 });

    // Clear the selection
    await page.getByTestId('clear-selection-button').click();

    // Wait for the selection pill to disappear
    await expect(page.getByTestId('clear-selection-button')).toBeHidden();

    // Remove the label filter and select all again
    await samplesPage.clickLabel(cocoDataset.labels.dog.name);
    await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.defaultPageSize, {
        timeout: 10000
    });

    await page.click('body');
    const allSampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/images/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await allSampleIdsResponse;

    // All samples should be selected (use selection pill since not all items are rendered)
    await expect(page.getByText(`${cocoDataset.totalSamples} selected`)).toBeVisible();
});

test('select all images respects annotation source filter', async ({ page, samplesPage }) => {
    await expect(samplesPage.getSamples().first()).toBeVisible();

    const sourceCheckboxes = page
        .getByText('Annotation Sources', { exact: true })
        .locator('xpath=ancestor::button/following-sibling::*[1]//button[@role="checkbox"]');

    await expect(sourceCheckboxes.first()).toBeVisible({ timeout: 10000 });
    test.skip(
        (await sourceCheckboxes.count()) < 2,
        'requires at least two annotation sources in the E2E dataset'
    );

    const listResponsePromise = page.waitForResponse(
        (response) =>
            response.url().includes('/images/list') &&
            response.request().method() === 'POST' &&
            response.status() === 200,
        { timeout: 10000 }
    );

    await sourceCheckboxes.first().click();
    const listResponse = await listResponsePromise;
    const listRequestBody = listResponse.request().postDataJSON();
    const expectedCollectionIds =
        listRequestBody.filters?.sample_filter?.annotations_filter?.collection_ids;

    expect(expectedCollectionIds?.length).toBeGreaterThan(0);

    await page.click('body');
    const sampleIdsResponsePromise = page.waitForResponse(
        (response) =>
            response.url().includes('/images/sample_ids') &&
            response.request().method() === 'POST' &&
            response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    const sampleIdsResponse = await sampleIdsResponsePromise;
    const sampleIdsRequestBody = sampleIdsResponse.request().postDataJSON();

    expect(sampleIdsRequestBody.filters?.sample_filter?.annotations_filter?.collection_ids).toEqual(
        expectedCollectionIds
    );
    await expect(page.getByText(/\d+ selected/)).toBeVisible();
});
