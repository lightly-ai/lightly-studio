import { expect, test } from '../utils';

test('Plot is visible only on samples page', async ({ samplesPage, page }) => {
    await samplesPage.goto();

    expect(page.getByTestId('toggle-plot-button')).toBeVisible();

    // TODO(Horatiu, 10/2025): Check why pressing the plot button will cause issues using Chromium
    // await page.getByTestId('toggle-plot-button').click();
    // expect(page.getByTestId('plot-panel')).toBeVisible();

    page.getByTestId('navigation-menu-annotations').click();

    await expect(page.getByTestId('annotations-grid')).toBeVisible({ timeout: 1000 });

    expect(page.getByTestId('toggle-plot-button')).not.toBeVisible();
    expect(page.getByTestId('plot-panel')).not.toBeVisible();
});
