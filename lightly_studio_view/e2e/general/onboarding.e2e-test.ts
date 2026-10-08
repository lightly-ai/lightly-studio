import { expect, gotoFirstPage, test } from '../utils';
import type { Page } from '@playwright/test';

test.skip(
    process.env.LIGHTLY_STUDIO_ONBOARDING_ENABLED !== 'true',
    'Run with LIGHTLY_STUDIO_ONBOARDING_ENABLED=true on the e2e server and Playwright process'
);

async function reachImageStep(page: Page) {
    await page.getByRole('button', { name: 'Start', exact: true }).click();
    await expect(page.getByText('Browse your collection', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    // Tag assign step — skip if visible
    if (await page.getByText('Tag your images', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    // Menu step — skip if visible
    if (await page.getByText('Run actions on your data', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    // Edit annotations step — skip if visible
    if (await page.getByText('Edit annotations', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    // Embedding step — skip if visible
    if (await page.getByText('Explore the embedding space', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    await expect(page.getByText('Open an image', { exact: true })).toBeVisible();
}

test('image tour follows a double-click into sample details', async ({ page, samplesPage }) => {
    await expect(page.getByRole('complementary', { name: 'Image tour invitation' })).toBeVisible();
    await reachImageStep(page);

    await samplesPage.getSampleByIndex(0).click();
    await expect(page.getByText('Open an image', { exact: true })).toBeVisible();
    await samplesPage.getSampleByIndex(0).dblclick();

    await expect(page.getByText('Inspect and annotate', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Done' }).click();
    await expect(page.getByText('Inspect and annotate', { exact: true })).not.toBeVisible();
});

test('tour can open a sample with its accessible action and replay from detail', async ({
    page
}) => {
    await gotoFirstPage(page);
    await expect(page.getByRole('complementary', { name: 'Image tour invitation' })).toBeVisible();
    await reachImageStep(page);
    await page.getByRole('button', { name: 'Open sample' }).click();
    await expect(page.getByText('Inspect and annotate', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Done' }).click();

    await page.getByTestId('menu-trigger').click();
    await page.getByTestId('menu-show-tour').click();
    await expect(page.getByText('Browse your collection', { exact: true })).toBeVisible();
});

test('dismissed invitation stays dismissed after reload', async ({ page }) => {
    await gotoFirstPage(page);
    await expect(page.getByRole('complementary', { name: 'Image tour invitation' })).toBeVisible();
    await page.getByRole('button', { name: 'Dismiss' }).click();
    await page.reload();
    await expect(
        page.getByRole('complementary', { name: 'Image tour invitation' })
    ).not.toBeVisible();
});
