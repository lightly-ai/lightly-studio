import { expect, gotoFirstPage, test } from '../utils';
import type { Page } from '@playwright/test';

test.skip(
    process.env.LIGHTLY_STUDIO_ONBOARDING_ENABLED !== 'true',
    'Run with LIGHTLY_STUDIO_ONBOARDING_ENABLED=true on the e2e server and Playwright process'
);

async function reachImageStep(page: Page) {
    await page.getByRole('button', { name: 'Start', exact: true }).click();
    await expect(page.getByText('Your image collection', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    // Menu step — skip it if visible
    if (await page.getByText('Tools menu', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    // Edit/Annotate step — skip if visible
    if (await page.getByText('Annotate', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    // Filter step — skip if visible
    if (
        (await page.getByText('Filter by tag', { exact: true }).isVisible()) ||
        (await page.getByText('Search by description', { exact: true }).isVisible())
    ) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    await expect(page.getByText('Select samples', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    // Tag assign step — skip if visible
    if (await page.getByText('Create a tag', { exact: true }).isVisible()) {
        await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    await expect(page.getByText('Open a sample', { exact: true })).toBeVisible();
}

test('image tour follows a double-click into sample details', async ({ page, samplesPage }) => {
    await expect(page.getByRole('complementary', { name: 'Image tour invitation' })).toBeVisible();
    await reachImageStep(page);

    await samplesPage.getSampleByIndex(0).click();
    await expect(page.getByText('Open an image', { exact: true })).toBeVisible();
    await samplesPage.getSampleByIndex(0).dblclick();

    await expect(page.getByText('Sample details', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Done' }).click();
    await expect(page.getByText('Sample details', { exact: true })).not.toBeVisible();
});

test('tour can open a sample with its accessible action and replay from detail', async ({
    page
}) => {
    await gotoFirstPage(page);
    await expect(page.getByRole('complementary', { name: 'Image tour invitation' })).toBeVisible();
    await reachImageStep(page);
    await page.getByRole('button', { name: 'Open sample' }).click();
    await expect(page.getByText('Sample details', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Done' }).click();

    await page.getByTestId('menu-trigger').click();
    await page.getByTestId('menu-show-tour').click();
    await expect(page.getByText('Image grid', { exact: true })).toBeVisible();
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
