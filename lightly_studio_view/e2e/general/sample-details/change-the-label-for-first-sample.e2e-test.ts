import { test, expect } from '../../utils';
import { cocoDataset } from '../fixtures';

test('user can change label for first sample', async ({ samplesPage, sampleDetailsPage }) => {
    // samplesPage fixture automatically navigates and loads samples
    await samplesPage.doubleClickFirstSample();

    await sampleDetailsPage.pageIsReady();

    await sampleDetailsPage.clickEditButton();

    // First sample has a cell phone annotation - change it to apple
    const prevLabel = cocoDataset.labels.cellPhone.name;
    await expect(sampleDetailsPage.getAnnotationBoxByLabel(prevLabel)).toBeVisible();

    await sampleDetailsPage.getLabelSelects().first().click();

    const newLabel = cocoDataset.labels.apple.name;
    await sampleDetailsPage.setLabel(newLabel);

    await expect(sampleDetailsPage.getAnnotationBoxByLabel(newLabel)).toBeVisible();
    await expect(sampleDetailsPage.getAnnotationBoxByLabel(prevLabel)).not.toBeVisible();

    // Change back to original label
    await sampleDetailsPage.getLabelSelects().first().click();
    await sampleDetailsPage.setLabel(prevLabel);

    await expect(sampleDetailsPage.getAnnotationBoxByLabel(prevLabel)).toBeVisible();
    await expect(sampleDetailsPage.getAnnotationBoxByLabel(newLabel)).not.toBeVisible();
});
