import { test, expect } from '../utils';
import { youtubeVisVideosDataset } from './fixtures/youtubeVisVideosDataset';

test('video query supports apply, disable, re-enable, reopen, and clear', async ({
    page,
    videosPage
}) => {
    const name = youtubeVisVideosDataset.airplaneVideo.name;
    const query = `file_name = "${name}"`;
    await page.getByTestId('side-panel-tabs-query').click();
    await expect(page.locator('.monaco-editor .view-lines')).toContainText('duration_s > 10');
    const defaultQueryResponse = page.waitForResponse(
        (response) =>
            response.request().method() === 'POST' &&
            new URL(response.url()).pathname.endsWith('/video/')
    );
    await page.getByTestId('query-editor-apply-button').click();
    expect((await defaultQueryResponse).status()).toBe(200);
    await page.locator('.monaco-editor .view-lines').first().click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type('dura');
    await page.keyboard.press('Control+Space');
    await expect(page.locator('.suggest-widget .monaco-list-row.focused')).toContainText(
        'duration_s'
    );
    await page.keyboard.press('Enter');
    await expect(page.locator('.monaco-editor .view-lines')).toContainText('duration_s');
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type(query);
    await expect(page.locator('.monaco-editor .squiggly-error')).toHaveCount(0);
    await page.getByTestId('query-editor-apply-button').click();
    await expect(videosPage.getVideos()).toHaveCount(1);
    await expect(videosPage.getVideoByName(name)).toBeVisible();
    await page.getByTestId('query-editor-close-button').click();

    await page.getByRole('checkbox', { name: 'Disable query filter' }).click();
    await expect.poll(() => videosPage.getVideos().count()).toBeGreaterThan(1);
    await page.getByRole('checkbox', { name: 'Enable query filter' }).click();
    await expect(videosPage.getVideos()).toHaveCount(1);
    await page.getByTestId('query-filter-chip-body').click();
    await expect(page.locator('.monaco-editor .view-lines')).toContainText(query);
    await expect(page.getByTestId('query-editor-apply-button')).toHaveText('Re-apply');

    // An image-only field must not replace the active video query.
    await page.locator('.monaco-editor .view-lines').first().click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type('created_at = "2025-01-01"');
    await page.getByTestId('query-editor-apply-button').click();
    await expect(page.getByText('Failed to translate query:', { exact: false })).toBeVisible();
    await expect(videosPage.getVideos()).toHaveCount(1);
    await page.getByTestId('query-editor-close-button').click();

    await page.getByRole('button', { name: 'Clear query filter' }).click();
    await expect(page.getByTestId('query-filter-chip')).not.toBeVisible();
    await expect.poll(() => videosPage.getVideos().count()).toBeGreaterThan(1);
});
