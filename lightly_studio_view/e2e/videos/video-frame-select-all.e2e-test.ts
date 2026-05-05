import { expect, test } from '../utils';
import { youtubeVisVideosDataset } from './fixtures';

test('select all video frames with label filter via keyboard shortcut', async ({
    page,
    videoFramesPage
}) => {
    // Apply a label filter to reduce the visible frames
    await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);
    const filteredCount = await videoFramesPage.getVideoFrames().count();
    expect(filteredCount).toBe(youtubeVisVideosDataset.labels.airplane.frameCount);

    // Press Cmd+A / Ctrl+A to select all filtered frames
    await page.click('body');
    const sampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/frame/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await sampleIdsResponse;

    // All filtered frames should be selected
    expect(await videoFramesPage.getNumSelectedSamples()).toBe(
        youtubeVisVideosDataset.labels.airplane.frameCount
    );

    // Wait for the success toast to disappear before proceeding
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(0, { timeout: 5000 });

    // Clear the selection
    await page.getByTestId('clear-selection-button').click();

    // Wait for the selection pill to disappear
    await expect(page.getByTestId('clear-selection-button')).toBeHidden();

    // Remove the label filter and select all again
    await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);
    await expect(videoFramesPage.getVideoFrames().first()).toBeVisible({ timeout: 10000 });

    await page.click('body');
    const allSampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/frame/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await allSampleIdsResponse;

    // All frames should be selected (use selection pill since not all items are rendered)
    await expect(page.getByText(`${youtubeVisVideosDataset.totalFrames} selected`)).toBeVisible();
});
