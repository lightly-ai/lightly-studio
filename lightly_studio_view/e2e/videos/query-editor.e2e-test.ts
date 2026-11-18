import type { CollectionView } from '$lib/api/lightly_studio_local';
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

test('queries same-frame detections, separate frames, frame times and temporal events', async ({
    page,
    videosPage
}) => {
    const response = await page.request.get('/api/collections');
    expect(response.ok()).toBe(true);
    const collections: CollectionView[] = await response.json();
    const fixture = collections.find((collection) => collection.name === 'video-query-fixture');
    if (!fixture) throw new Error('Missing video-query-fixture dataset');
    await page.goto(`/datasets/${fixture.collection_id}/video/${fixture.collection_id}/videos`);

    const same = '0a275e7f12.mp4';
    const separate = '0a2f2bd294.mp4';
    const car = 'object_detection(class_name = "car")';
    const person = 'object_detection(class_name = "person")';
    await page.getByTestId('side-panel-tabs-query').click();
    for (const [query, expected] of [
        [`frame(${car} AND ${person})`, [same]],
        [`frame(${car}) AND frame(${person})`, [same, separate]],
        [`frame(frame_timestamp_s > 0 AND ${car})`, [separate]],
        ['event(class_name = "run")', [same, separate]],
        ['classification(class_name = "run")', [separate]],
        ['event(class_name = "run" AND start_time_s < 1)', [same]]
    ] as const) {
        await page.locator('.monaco-editor .view-lines').first().click();
        await page.keyboard.press('ControlOrMeta+a');
        await page.keyboard.insertText(query);
        const applied = page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                new URL(response.url()).pathname.endsWith('/video/') &&
                Boolean(response.request().postDataJSON()?.filter?.sample_filter?.query_expr)
        );
        await page.getByTestId('query-editor-apply-button').click();
        expect((await applied).status()).toBe(200);
        await expect(videosPage.getVideos()).toHaveCount(expected.length);
        for (const name of expected) await expect(videosPage.getVideoByName(name)).toBeVisible();
    }

    await page.getByTestId('query-editor-close-button').click();
    await page.click('body');
    await page.keyboard.press('ControlOrMeta+a');
    await expect(page.getByText('1 selected', { exact: true })).toBeVisible();
    await expect(videosPage.getVideoByName(same).getByTestId('sample-selected-box')).toBeChecked();

    await page.getByTestId('navigation-menu-frames').click();
    await page.getByRole('option', { name: 'Frames', exact: true }).click();
    await expect(page.getByTestId('frame-grid-item').first()).toBeVisible();
    await expect(page.getByTestId('query-filter-chip')).toHaveCount(0);
});
