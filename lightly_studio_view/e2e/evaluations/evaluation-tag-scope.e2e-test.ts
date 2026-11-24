import { expect, gotoFirstPage, test } from '../utils';

const RUN_NAME = 'e2e-tag-scoped-run';
const TAG_NAME = 'distribution_reviewed';

test('creates an evaluation run on the images of a tag', async ({ page }) => {
    await gotoFirstPage(page);
    await page.getByTestId('side-panel-tabs-eval').click();
    await page.getByTestId('evaluation-runs-add-button').click();

    const dialog = page.getByRole('dialog');
    await dialog.getByTestId('gt-source-select').click();
    await page.getByRole('option', { name: 'COCO annotations', exact: true }).click();
    await dialog.getByTestId('pred-source-select').click();
    await page.getByRole('option', { name: 'YOLOv8-m inferences', exact: true }).click();
    await dialog.getByRole('checkbox', { name: TAG_NAME }).click();
    await dialog.getByTestId('evaluation-name-input').fill(RUN_NAME);
    await dialog.getByTestId('trigger-evaluation-submit').click();

    const run = page.getByTestId(`evaluation-run-item-${RUN_NAME}`);
    await expect(run).toBeVisible();
    await expect(run.getByTestId('evaluation-run-scope')).toHaveText(`Images: ${TAG_NAME}`);
});
