import { expect, test } from '../utils';
import { cocoDataset } from './fixtures';

test('select all images with label filter via keyboard shortcut', async ({ page, samplesPage }) => {
    // Apply a label filter to reduce the visible samples
    await samplesPage.clickLabel(cocoDataset.labels.dog.name);
    const filteredCount = await samplesPage.getSamples().count();
    expect(filteredCount).toBe(cocoDataset.labels.dog.sampleCount);

    // Press Cmd+A / Ctrl+A to select all filtered samples
    const sampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/images/sample_ids') && response.status() === 200
    );
    await page.keyboard.press('Meta+A');
    await sampleIdsResponse;

    // All filtered samples should be selected
    expect(await samplesPage.getNumSelectedSamples()).toBe(cocoDataset.labels.dog.sampleCount);

    // Remove the label filter and select all again
    await samplesPage.clickLabel(cocoDataset.labels.dog.name);
    await samplesPage.getSamples().first().waitFor({ state: 'attached', timeout: 10000 });

    const allSampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/images/sample_ids') && response.status() === 200
    );
    await page.keyboard.press('Meta+A');
    await allSampleIdsResponse;

    // All samples should be selected
    expect(await samplesPage.getNumSelectedSamples()).toBe(cocoDataset.totalSamples);
});
