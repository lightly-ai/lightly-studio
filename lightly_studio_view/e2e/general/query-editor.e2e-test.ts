import type { Page, Response } from '@playwright/test';
import type { ReadImagesData, ReadImagesResponse } from '$lib/api/lightly_studio_local';
import { test, expect } from '../utils';
import { cocoDataset } from './fixtures';

const QUERY = 'segmentation_mask(class_name = "airplane")';

function waitForImageListResponse(page: Page): Promise<Response> {
    return page.waitForResponse((r) => r.url().includes('/images/list') && r.status() === 200);
}

/** Select-all in Monaco, type a query, click Apply, and wait for the grid to update. */
async function typeAndApply(page: Page, query: string): Promise<void> {
    await page.locator('.monaco-editor .view-lines').first().click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type(query);

    const refetchPromise = waitForImageListResponse(page);
    await page.getByTestId('query-editor-apply-button').click();
    await refetchPromise;
}

test.describe('query editor', () => {
    test('send metadata comparisons and display the filtered response', async ({
        samplesPage,
        page
    }) => {
        // Mock only this query's response so the shared dataset needs no test-specific metadata.
        await page.route('**/images/list', async (route) => {
            const body: ReadImagesData['body'] = route.request().postDataJSON();
            if (!body.filters?.sample_filter?.query_expr) {
                await route.continue();
                return;
            }

            const response = await route.fetch({ postData: { ...body, filters: null } });
            const images: ReadImagesResponse = await response.json();
            const data = images.data.filter(
                (sample) => sample.file_name === cocoDataset.firstSampleName
            );
            await route.fulfill({
                response,
                json: { data, total_count: data.length, nextCursor: null }
            });
        });
        const queryRequest = page.waitForRequest((request) => {
            if (!request.url().endsWith('/images/list') || request.method() !== 'POST') {
                return false;
            }
            const body: ReadImagesData['body'] = request.postDataJSON();
            return !!body.filters?.sample_filter?.query_expr;
        });
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(
            page,
            'metadata["camera"] = "front" AND metadata["reviewed"] = true AND metadata["odometry.acc[1]"] < -0.2'
        );

        const body: ReadImagesData['body'] = (await queryRequest).postDataJSON();
        expect(body.filters?.sample_filter?.query_expr).toEqual({
            match_expr: {
                type: 'and',
                children: [
                    {
                        type: 'metadata_comparison_expr',
                        path: 'camera',
                        operator: '==',
                        value: 'front'
                    },
                    {
                        type: 'metadata_comparison_expr',
                        path: 'reviewed',
                        operator: '==',
                        value: true
                    },
                    {
                        type: 'metadata_comparison_expr',
                        path: 'odometry.acc[1]',
                        operator: '<',
                        value: -0.2
                    }
                ]
            }
        });
        await expect(samplesPage.getSamples()).toHaveCount(1);
        await expect(samplesPage.getSampleByName(cocoDataset.firstSampleName)).toBeVisible();
        await expect(page.getByTestId('query-filter-chip')).toBeVisible();
    });

    test('apply query and verify filtered grid', async ({ samplesPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await expect(page.getByRole('heading', { name: 'Query Filter' })).toBeVisible();

        // On first open: The apply button should be enabled.
        await expect(page.getByTestId('query-editor-apply-button')).toBeEnabled();

        await typeAndApply(page, QUERY);

        // Verify the grid shows only airplane samples
        await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.labels.airplane.sampleCount);

        // Apply button stays enabled to allow refreshing data (draft matches applied value)
        await expect(page.getByTestId('query-editor-apply-button')).toBeEnabled();
        await expect(page.getByTestId('query-editor-apply-button')).toHaveText('Re-apply');

        // Filter chip should be visible
        await expect(page.getByTestId('query-filter-chip')).toBeVisible();
    });

    test('toggling filter chip disables and re-enables query', async ({ samplesPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(page, QUERY);
        await expect(page.getByTestId('query-filter-chip')).toBeVisible();
        await page.getByTestId('query-editor-close-button').click();

        // Uncheck the filter chip checkbox to disable the query
        const disableRefetch = waitForImageListResponse(page);
        await page.getByRole('checkbox', { name: 'Disable query filter' }).click();
        await disableRefetch;

        // Grid should show at least one full page of unfiltered results.
        // (Infinite scroll may load additional pages, so we check ≥ rather than ===.)
        await expect
            .poll(() => samplesPage.getSamples().count())
            .toBeGreaterThanOrEqual(cocoDataset.defaultPageSize);

        // Re-check to re-enable the query
        const enableRefetch = waitForImageListResponse(page);
        await page.getByRole('checkbox', { name: 'Enable query filter' }).click();
        await enableRefetch;

        await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.labels.airplane.sampleCount);
    });

    test('reopening editor loads existing query with Re-apply enabled', async ({
        samplesPage,
        page
    }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(page, QUERY);
        await page.getByTestId('query-editor-close-button').click();

        // Click the chip body to reopen the editor
        await page.getByTestId('query-filter-chip-body').click();
        await expect(page.getByRole('heading', { name: 'Query Filter' })).toBeVisible();

        // Editor should contain the previously applied query
        await expect(page.locator('.monaco-editor .view-lines')).toContainText(QUERY);

        // Re-apply is offered since the editor holds the applied query
        await expect(page.getByTestId('query-editor-apply-button')).toBeEnabled();
        await expect(page.getByTestId('query-editor-apply-button')).toHaveText('Re-apply');

        // Grid should still show filtered results
        await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.labels.airplane.sampleCount);
    });

    test('clearing filter removes chip and restores grid', async ({ samplesPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(page, QUERY);
        await page.getByTestId('query-editor-close-button').click();

        // Click the X button to clear the filter
        const refetchPromise = waitForImageListResponse(page);
        await page.getByRole('button', { name: 'Clear query filter' }).click();
        await refetchPromise;

        // Filter chip should no longer be visible
        await expect(page.getByTestId('query-filter-chip')).not.toBeVisible();

        // Grid should show at least one full page of unfiltered results
        await expect
            .poll(() => samplesPage.getSamples().count())
            .toBeGreaterThanOrEqual(cocoDataset.defaultPageSize);
    });

    test('syntax error shows toast and Apply stays enabled', async ({ samplesPage, page }) => {
        await page.getByTestId('side-panel-tabs-query').click();
        await typeAndApply(page, QUERY);

        // Now type an invalid query over the existing one
        await page.locator('.monaco-editor .view-lines').first().click();
        await page.keyboard.press('ControlOrMeta+a');
        await page.keyboard.type('width <');

        const applyButton = page.getByTestId('query-editor-apply-button');
        await applyButton.click();

        // Error toast should appear
        await expect(page.getByText('Failed to translate query')).toBeVisible();

        // Apply button should remain enabled (draft still differs from last applied)
        await expect(applyButton).toBeEnabled();

        // Grid should still show the previously filtered results
        await expect(samplesPage.getSamples()).toHaveCount(cocoDataset.labels.airplane.sampleCount);
    });
});
