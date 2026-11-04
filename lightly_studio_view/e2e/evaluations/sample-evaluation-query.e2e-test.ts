import type { Page } from '@playwright/test';
import { expect, gotoFirstPage, test } from '../utils';

const RUN_NAME = 'evaluation-example-tagged-samples';
const RUN_QUERY = `sample_evaluation(name = "${RUN_NAME}")`;
const TAGGED_SAMPLE_COUNT = 10;

async function typeQuery(page: Page, query: string): Promise<void> {
    await page.locator('.monaco-editor .view-lines').first().click();
    await page.keyboard.press('ControlOrMeta+a');
    await page.keyboard.type(query);
    await page.keyboard.press('Escape');
}

async function applyQuery(page: Page): Promise<void> {
    const response = page.waitForResponse(
        (response) => response.url().includes('/images/list') && response.status() === 200
    );
    await page.getByTestId('query-editor-apply-button').click();
    await response;
}

async function applyRunQuery(page: Page): Promise<void> {
    await typeQuery(page, RUN_QUERY);
    await applyQuery(page);
    await expect(page.getByTestId('sample-grid-item')).toHaveCount(TAGGED_SAMPLE_COUNT);
}

test.beforeEach(async ({ page }) => {
    await gotoFirstPage(page);
    await page.getByTestId('side-panel-tabs-query').click();
    await expect(page.getByRole('heading', { name: 'Query Filter' })).toBeVisible();
});

test('run membership returns the evaluated samples', async ({ page }) => {
    const samples = page.getByTestId('sample-grid-item');
    await typeQuery(page, '"evaluated_samples" IN tags');
    await applyQuery(page);
    await expect(samples).toHaveCount(TAGGED_SAMPLE_COUNT);
    const names = await samples.evaluateAll((items) =>
        items.map((item) => item.getAttribute('data-sample-name'))
    );

    await applyRunQuery(page);
    const evaluatedNames = await samples.evaluateAll((items) =>
        items.map((item) => item.getAttribute('data-sample-name'))
    );
    expect(evaluatedNames.sort()).toEqual(names.sort());
    await expect(page.getByTestId('query-filter-chip')).toBeVisible();
});

for (const quote of ['"', "'"]) {
    test(`filters metrics with ${quote} quotes and nested Boolean expressions`, async ({
        page
    }) => {
        // The fixture uses identical ground truth and predictions: fp and fn are zero.
        await applyRunQuery(page);
        const metric = (name: string) => `${quote}${name}${quote}`;
        await typeQuery(
            page,
            `width > 0 AND sample_evaluation(name = ${quote}${RUN_NAME}${quote} AND ` +
                `(${metric('tp')} >= 0 OR ${metric('fn')} > 0) AND NOT ${metric('fp')} != 0)`
        );
        await applyQuery(page);
        await expect(page.getByTestId('sample-grid-item')).toHaveCount(TAGGED_SAMPLE_COUNT);

        await typeQuery(page, `sample_evaluation(name = "${RUN_NAME}" AND ${metric('fn')} > 0)`);
        await applyQuery(page);
        await expect(page.getByTestId('sample-grid-item')).toHaveCount(0);
    });

    test(`autocomplete replaces a partially quoted metric starting with ${quote}`, async ({
        page
    }) => {
        await applyRunQuery(page);
        await typeQuery(page, `sample_evaluation(name = "${RUN_NAME}" AND ${quote}t`);
        await page.keyboard.press('Control+Space');
        const suggestion = page.getByRole('option', { name: /^"tp",/ });
        await expect(suggestion).toBeVisible();
        await suggestion.click();
        await page.keyboard.type(' >= 0)');
        await page.keyboard.press('Escape');
        await applyQuery(page);
        await expect(page.getByTestId('sample-grid-item')).toHaveCount(TAGGED_SAMPLE_COUNT);
    });
}

test('unquoted metrics show an error and preserve the applied filter', async ({ page }) => {
    await applyRunQuery(page);

    await typeQuery(page, `sample_evaluation(name = "${RUN_NAME}" AND tp > 0)`);
    await page.getByTestId('query-editor-apply-button').click();
    await expect(page.getByText(/Failed to translate query/)).toBeVisible();
    await expect(page.getByTestId('sample-grid-item')).toHaveCount(TAGGED_SAMPLE_COUNT);
    await expect(page.getByTestId('query-editor-apply-button')).toBeEnabled();
});
