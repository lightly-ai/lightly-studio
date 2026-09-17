import { expect, test } from '../utils';
import { cocoDataset } from '../general/fixtures';

const RUN_NAME = 'evaluation-example-all-samples';
const IOU_SORT_LABEL = `${RUN_NAME}.iou`;

test('hides the detail-view stale warning while a similarity search drives prev/next', async ({
    page,
    annotationsPage,
    annotationDetailsPage
}) => {
    // Sort the grid by the run's per-annotation IoU. This is the sort prev/next follows.
    await page.getByTestId('sort-by-trigger').click();
    await page.getByRole('option', { name: IOU_SORT_LABEL, exact: true }).click();

    // Editing any annotation in the source marks every run over it stale.
    await annotationsPage.startEditing();
    await annotationsPage.selectAnnotation(0);
    await annotationsPage.setLabel(cocoDataset.labels.bear.name);
    await expect(page.getByTestId('annotation-sort-stale-icon')).toBeVisible();

    // Positive control: with no search the sort is what prev/next follows, so the detail
    // view must warn. Without this, the final assertion could pass vacuously.
    await annotationsPage.clickAnnotation(0);
    await annotationDetailsPage.waitForNavigation();
    await expect(page.getByTestId('annotation-navigation-stale-icon')).toBeVisible();

    // Back to the grid client-side only: the active sort lives in an unpersisted
    // module-level store, so a reload would drop it and void the rest of the test.
    await page.goBack();
    await expect(page.getByTestId('annotations-grid')).toBeVisible();

    // A text search takes precedence: useAdjacentAnnotations drops annotation_sort_by
    // whenever textEmbedding is set, so prev/next is similarity-ordered from here on.
    const searchInput = page.getByTestId('text-embedding-search-input');
    await expect(searchInput).toBeVisible();
    const searchResponse = page.waitForResponse(
        (response) => response.url().includes('query_text=bear') && response.status() === 200
    );
    await searchInput.fill('bear');
    await page.keyboard.press('Enter');
    await searchResponse;

    // The grid disables its own sort control for the same reason.
    await expect(page.getByTestId('sort-by-trigger')).toBeDisabled();

    await annotationsPage.clickAnnotation(0);
    await annotationDetailsPage.waitForNavigation();

    // The stale run has no bearing on the order being stepped through, so the warning
    // must not claim it does.
    await expect(page.getByTestId('annotation-navigation-stale-icon')).toBeHidden();
});
