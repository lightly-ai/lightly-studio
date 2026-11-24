import { expect, gotoFirstPage, test } from '../utils';

const TAGGED_SAMPLES_EVALUATION_RUN_NAME = 'evaluation-example-tagged-samples';
const ALL_SAMPLES_EVALUATION_RUN_NAME = 'evaluation-example-all-samples';
const DECIMAL_METRIC = /^\d\.\d{3}$/;

test('compares two evaluation runs on a leaderboard', async ({ page }) => {
    await gotoFirstPage(page);
    await page.getByTestId('side-panel-tabs-eval').click();
    await expect(page.getByTestId('evaluation-runs-panel')).toBeVisible();

    await page
        .getByRole('checkbox', {
            name: `Select ${TAGGED_SAMPLES_EVALUATION_RUN_NAME} for comparison`
        })
        .click();
    await page
        .getByRole('checkbox', { name: `Select ${ALL_SAMPLES_EVALUATION_RUN_NAME} for comparison` })
        .click();
    await page.getByTestId('compare-evaluation-runs-button').click();

    await expect(page).toHaveURL(/\/evaluation\/compare\?runs=/);
    const leaderboard = page.getByTestId('evaluation-leaderboard');
    await expect(leaderboard.getByRole('row')).toHaveCount(3);
    const firstMapCell = leaderboard.getByRole('row').nth(1).getByRole('cell').nth(1);
    await expect(firstMapCell).toHaveText(DECIMAL_METRIC);
    // The two runs use different annotation sources and image sets.
    await expect(page.getByText('Runs evaluate different images.')).toBeVisible();
    await expect(page.getByTestId('per-class-metrics')).toBeVisible();

    await page
        .getByTestId('scenario-tag-picker')
        .getByRole('checkbox', { name: 'distribution_reviewed' })
        .click();
    await expect(page).toHaveURL(/tags=/);
    const scenarioRow = page
        .getByTestId('scenario-table')
        .getByRole('row', { name: /distribution_reviewed/ });
    await expect(scenarioRow.getByRole('cell').nth(1)).toHaveText(DECIMAL_METRIC);
});
