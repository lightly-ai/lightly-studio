import { expect, test } from '../../utils';
import { bearSamples, cocoCollection } from '../fixtures';

test('user can change label within the selected label', async ({
    samplesPage,
    sampleDetailsPage
}) => {
    const oldLabel = cocoCollection.labels.bear.name;
    const newLabel = cocoCollection.labels.baseballBat.name;
    const updatedSampleName = bearSamples[0].name;

    const bearSamplesCount = cocoCollection.labels.bear.sampleCount;
    const baseballBatSamplesCount = cocoCollection.labels.baseballBat.sampleCount;

    // Check initial state
    await samplesPage.clickLabel(newLabel);
    await expect(samplesPage.getSamples()).toHaveCount(baseballBatSamplesCount);
    await samplesPage.clickLabel(newLabel);
    await samplesPage.clickLabel(oldLabel);
    await expect(samplesPage.getSamples()).toHaveCount(bearSamplesCount);

    // Update first sample
    await samplesPage.doubleClickFirstSample();
    await sampleDetailsPage.clickEditButton();

    expect(await sampleDetailsPage.hasAnnotationWithLabel(newLabel)).not.toBeTruthy();
    await expect(sampleDetailsPage.getSampleName()).toHaveText(updatedSampleName);
    await sampleDetailsPage.setFirstAnnotationLabel(newLabel);
    await expect(sampleDetailsPage.hasAnnotationWithLabel(newLabel)).toBeTruthy();

    // Check what changes are reflected withing the label selection
    await samplesPage.goto();
    await samplesPage.clickLabel(oldLabel);
    await expect(samplesPage.getSamples()).toHaveCount(bearSamplesCount - 1);
    await samplesPage.clickLabel(oldLabel);
    await samplesPage.clickLabel(newLabel);
    await expect(samplesPage.getSamples()).toHaveCount(baseballBatSamplesCount + 1);

    // Revert changes
    await samplesPage.doubleClickNthSample(1);
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
    await expect(samplesPage.getSamples()).toHaveCount(bearSamplesCount);
});
