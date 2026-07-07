import { expect, gotoFirstPage, test } from '../utils';

const ALL_SAMPLES_EVALUATION_RUN_NAME = 'evaluation-example-all-samples';
const ALL_SAMPLES_EVALUATION_RUN_TEST_ID = 'evaluation-run-item-evaluation-example-all-samples';

test('shows evaluation run details from indexed backend data', async ({ page }) => {
    await gotoFirstPage(page);

    await expect(page.getByRole('button', { name: 'Annotation Sources' })).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'COCO annotations' })).toBeChecked();
    await expect(page.getByRole('checkbox', { name: 'YOLOv8-m inferences' })).toBeChecked();

    await expect(page.getByTestId('side-panel-tabs-eval')).toBeVisible();
    await page.getByTestId('side-panel-tabs-eval').click();

    await expect(page.getByTestId('evaluation-runs-panel')).toBeVisible();
    await expect(page.getByText('evaluation-example-tagged-samples')).toBeVisible();
    await expect(page.getByText(ALL_SAMPLES_EVALUATION_RUN_NAME)).toBeVisible();

    const run = page.getByTestId(ALL_SAMPLES_EVALUATION_RUN_TEST_ID);
    await expect(run).toHaveCount(1);

    const confusionMatrixResponse = page.waitForResponse(
        (response) => response.url().includes('/confusion-matrix') && response.status() === 200
    );
    await run.click();
    await confusionMatrixResponse;

    await expect(page.getByTestId('evaluation-run-config')).toContainText('iou_threshold');
    await expect(page.getByTestId('evaluation-run-config')).toContainText('0.5');
    await expect(page.getByTestId('evaluation-run-config')).toContainText('classwise');
    await expect(page.getByTestId('evaluation-run-config')).toContainText('true');
    await expect(page.getByTestId('evaluation-run-gt-annotation-source')).toHaveText(
        'COCO annotations'
    );
    await expect(page.getByTestId('evaluation-run-prediction-annotation-source')).toHaveText(
        'YOLOv8-m inferences'
    );
    await expect(page.getByTestId('confusion-matrix')).toBeVisible();
});
