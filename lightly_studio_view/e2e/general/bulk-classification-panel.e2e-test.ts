import { test, expect } from '../utils';
import { cocoDataset } from './fixtures';

test('user can pick an annotation source and class for a selection', async ({ samplesPage }) => {
    await samplesPage.startEditing();
    await samplesPage.getSampleByIndex(0).click();

    await expect(
        samplesPage.page.getByRole('heading', { name: 'Selected images: 1' })
    ).toBeVisible();
    await expect(samplesPage.getBulkClassificationApplyButton()).toBeDisabled();

    await samplesPage.pickBulkClassificationName('Annotation class', cocoDataset.labels.apple.name);

    await expect(samplesPage.getBulkClassificationPicker('Annotation class')).toContainText(
        cocoDataset.labels.apple.name
    );
    await expect(samplesPage.getBulkClassificationApplyButton()).toBeEnabled();
});
