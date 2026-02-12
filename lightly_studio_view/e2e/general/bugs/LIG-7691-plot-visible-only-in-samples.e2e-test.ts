import { expect, test } from '../../utils';

test('Plot is visible only on samples page', async ({ samplesPage, page }) => {
    await samplesPage.goto();

    const togglePlotButton = page.getByTestId('toggle-plot-button');
    const plotPanel = page.getByTestId('plot-panel');
    const plotControls = page.getByTestId('plot-panel-controls');
    const resetViewButton = page.getByTestId('plot-reset-view-button');
    const rectangleSelectionButton = page.locator('button[title*="rectangle selection mode"]');
    const lassoSelectionButton = page.locator('button[title*="lasso selection mode"]');

    await expect(togglePlotButton).toBeVisible();

    // TODO(Horatiu, 10/2025): Historically, toggling the plot was flaky in Chromium.
    // Keep this regression coverage and monitor CI stability.
    // Repeat the open/close cycle to catch intermittent rendering issues.
    for (let i = 0; i < 3; i++) {
        await togglePlotButton.click();
        await expect(plotPanel).toBeVisible();
        await expect(plotControls).toBeVisible();
        await expect(resetViewButton).toBeVisible();
        await expect(rectangleSelectionButton).toBeVisible();
        await expect(lassoSelectionButton).toBeVisible();

        await togglePlotButton.click();
        await expect(plotPanel).not.toBeVisible();
    }

    await page.getByTestId('navigation-menu-annotations').click();

    await expect(page.getByTestId('annotations-grid')).toBeVisible({ timeout: 1000 });

    await expect(page.getByTestId('toggle-plot-button')).not.toBeVisible();
    await expect(page.getByTestId('plot-panel')).not.toBeVisible();
});
