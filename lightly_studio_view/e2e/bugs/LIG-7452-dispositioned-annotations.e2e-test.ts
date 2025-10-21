import { Locator } from '@playwright/test';
import { test, expect } from '../utils';
import { multipleAnnotationsSample, airplaneSamples } from '../fixtures';

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

    // Select the label "airplane"
    await samplesPage.clickLabel('airplane');

    expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).not.toBeVisible();
    expect(samplesPage.getSampleByName(airplaneSamples[1].name)).toBeVisible();

    // Check airplane box coordinates
    airplaneSamples[1].annotations.forEach(({ label, coordinates }) =>
        expectBoxCoordinates(
            samplesPage.getAnnotationByLabel(airplaneSamples[1].name, label),
            coordinates
        )
    );

    // Unselect the label "airplane"
    await samplesPage.clickLabel('airplane');

    // Check that we have the sample without airplane again
    expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).toBeVisible();
    multipleAnnotationsSample.annotations.forEach(({ label, coordinates }) =>
        expectBoxCoordinates(
            samplesPage.getAnnotationByLabel(multipleAnnotationsSample.name, label),
            coordinates
        )
    );
});
