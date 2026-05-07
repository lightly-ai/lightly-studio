import { expect, test } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test('select all video frames with label filter via keyboard shortcut', async ({
    page,
    videoFramesPage
}) => {
    // Apply a label filter to reduce the visible frames
    await videoFramesPage.clickLabel(youtubeVisVideosDataset.labels.airplane.name);
    await expect(videoFramesPage.getVideoFrames().first()).toBeVisible({ timeout: 10000 });

    // Press Cmd+A / Ctrl+A to select all filtered frames
    await page.click('body');
    const sampleIdsResponse = page.waitForResponse(
        (response) => response.url().includes('/frame/sample_ids') && response.status() === 200,
        { timeout: 10000 }
    );
    await page.keyboard.press('Control+a');
    await sampleIdsResponse;

    // All filtered frames should be selected (use selection pill since grid uses infinite scroll)
    await expect(
        page.getByText(`${youtubeVisVideosDataset.labels.airplane.frameCount} selected`)
    ).toBeVisible();

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

    // All frames should be selected. Since we don't track total frames in the fixture,
    // assert the selection pill shows a count greater than the filtered count.
    const selectionText = await page.getByText(/\d+ selected/).textContent();
    expect(selectionText).not.toBeNull();
    const selectedCount = parseInt(selectionText!.split(' ')[0], 10);
    expect(selectedCount).toBeGreaterThan(youtubeVisVideosDataset.labels.airplane.frameCount);
});
