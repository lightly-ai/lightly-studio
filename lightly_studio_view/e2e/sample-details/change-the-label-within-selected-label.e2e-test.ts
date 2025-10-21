import { expect, test } from '../utils';
import { airplaneSamples, cocoDataset } from '../fixtures';

test('user can change label within the selected label', async ({
    samplesPage,
    sampleDetailsPage
}) => {
    const oldLabel = cocoDataset.labels.airplane.name;
    const newLabel = cocoDataset.labels.baseballBat.name;
    const updatedSampleName = airplaneSamples[0].name;

    const airplaneSamplesCount = cocoDataset.labels.airplane.sampleCount;
    const baseballBatSamplesCount = cocoDataset.labels.baseballBat.sampleCount;

    // Check initial state
    await samplesPage.clickLabel(newLabel);
    await expect(samplesPage.getSamples()).toHaveCount(baseballBatSamplesCount);
    await samplesPage.clickLabel(newLabel);
    await samplesPage.clickLabel(oldLabel);
    await expect(samplesPage.getSamples()).toHaveCount(airplaneSamplesCount);

    // Update first sample
    await samplesPage.doubleClickFirstSample();
    await sampleDetailsPage.clickEditButton();

    expect(await sampleDetailsPage.hasAnnotationWithLabel(newLabel)).not.toBeTruthy();
    await expect(sampleDetailsPage.getSampleName()).toHaveText(updatedSampleName);
    await sampleDetailsPage.setFirstAnnotationLabel(newLabel);
    await expect(sampleDetailsPage.hasAnnotationWithLabel(newLabel)).toBeTruthy();

    // Navigate to next sample (second airplane sample)
    await sampleDetailsPage.gotoNextSampleByKeyboard();
    await expect(sampleDetailsPage.getSampleName()).toHaveText(airplaneSamples[1].name);
    expect(await sampleDetailsPage.hasAnnotationWithLabel(newLabel)).not.toBeTruthy();

    // Check what changes are reflected withing the label selection
    await samplesPage.goto();
    await samplesPage.clickLabel(oldLabel);
    await expect(samplesPage.getSamples()).toHaveCount(airplaneSamplesCount - 1);
    await samplesPage.clickLabel(oldLabel);
    await samplesPage.clickLabel(newLabel);
    await expect(samplesPage.getSamples()).toHaveCount(baseballBatSamplesCount + 1);

    // Revert changes
    await samplesPage.getSamples().nth(1).dblclick();
    await expect(sampleDetailsPage.getSampleName()).toHaveText(updatedSampleName);
    await expect(sampleDetailsPage.hasAnnotationWithLabel(newLabel)).toBeTruthy();
    await sampleDetailsPage.clickEditButton();
    await sampleDetailsPage.setFirstAnnotationLabel(oldLabel);
    await expect(sampleDetailsPage.hasAnnotationWithLabel(oldLabel)).toBeTruthy();

    // Check what changes are reverted withing the label selection
    await samplesPage.goto();
    await samplesPage.clickLabel(newLabel);
    await expect(samplesPage.getSamples()).toHaveCount(baseballBatSamplesCount);
    await samplesPage.clickLabel(newLabel);
    await samplesPage.clickLabel(oldLabel);
    await expect(samplesPage.getSamples()).toHaveCount(airplaneSamplesCount);
});
