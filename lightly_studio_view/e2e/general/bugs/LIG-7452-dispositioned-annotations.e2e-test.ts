import { Locator } from '@playwright/test';
import { test, expect } from '../../utils';
import { multipleAnnotationsSample, bearSamples, cocoCollection } from '../fixtures';

const expectBoxCoordinates = (
    box: Locator,
    { x, y, width, height }: { x: number; y: number; width: number; height: number }
) => {
    expect(box).toHaveAttribute('x', x.toString());
    expect(box).toHaveAttribute('y', y.toString());
    expect(box).toHaveAttribute('width', width.toString());
    expect(box).toHaveAttribute('height', height.toString());
};

test('Annotations should have correct position between annotation label selection', async ({
    samplesPage
}) => {
    await samplesPage.goto();

    // Check that we have the sample without airplane
    expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).toBeVisible();

    // Check that we have the sample with annotations
    multipleAnnotationsSample.annotations.forEach(({ label, coordinates }) =>
        expectBoxCoordinates(
            samplesPage.getAnnotationByLabel(multipleAnnotationsSample.name, label),
            coordinates
        )
    );

    // Select the label "bear"
    const bearLabel = cocoCollection.labels.bear.name;
    expect(bearLabel).toStrictEqual('bear');

    await samplesPage.clickLabel(bearLabel);

    expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).not.toBeVisible();
    expect(samplesPage.getSampleByName(bearSamples[1].name)).toBeVisible();

    // Check bear box coordinates
    const bearLocators = await samplesPage.getAnnotationsByLabel(bearSamples[1].name, 'bear');
    expect(bearLocators.length).toBe(bearSamples[1].annotations.length);
    for (let i = 0; i < bearSamples[1].annotations.length; i++) {
        expectBoxCoordinates(bearLocators[i], bearSamples[1].annotations[i].coordinates);
    }

    // Unselect the label "bear"
    await samplesPage.clickLabel(bearLabel);

    // Check that we have the sample without bear again
    expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).toBeVisible();
    multipleAnnotationsSample.annotations.forEach(({ label, coordinates }) =>
        expectBoxCoordinates(
            samplesPage.getAnnotationByLabel(multipleAnnotationsSample.name, label),
            coordinates
        )
    );
});
