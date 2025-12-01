import { test, expect } from './utils';
import { multipleAnnotationsSample, bearSamples, cocoDataset } from './fixtures';

test.beforeEach(async ({ annotationsPage }) => {
    await annotationsPage.goto();
});

test('user can navigate to first annotation details', async ({
    annotationsPage,
    annotationDetailsPage
}) => {
    await annotationsPage.clickAnnotation(0);

    await expect(annotationDetailsPage.getSampleName()).toHaveText(multipleAnnotationsSample.name);

    await expect(annotationDetailsPage.getAnnotationBoxes()).toHaveCount(1);

    // First annotation is "cell phone"
    const cellPhoneAnnotation = multipleAnnotationsSample.annotations.find(
        (a) => a.label === cocoDataset.labels.cellPhone.name
    )!;
    await annotationDetailsPage.verifyDimensions(
        cellPhoneAnnotation.coordinates.width,
        cellPhoneAnnotation.coordinates.height
    );
});

test('user can navigate with stepping navigation with label', async ({
    annotationsPage,
    annotationDetailsPage
}) => {
    // Filter by bear label to get all bear annotations.
    await annotationsPage.clickLabel(cocoDataset.labels.bear.name);

    // Get all bear annotations from fixtures in order.
    const bearAnnotations = bearSamples.flatMap((sample) => sample.annotations);

    let i = 0;
    await annotationsPage.clickAnnotation(i);

    // Iterate through all bear annotations and verify dimensions + navigation.
    for (i; i < bearAnnotations.length; i++) {
        const annotation = bearAnnotations[i];

        await annotationDetailsPage.verifyDimensions(
            annotation.coordinates.width,
            annotation.coordinates.height
        );

        // Check navigation button visibility based on position.
        if (i === 0) {
            await expect(annotationDetailsPage.getPrevButton()).not.toBeVisible();
        } else {
            await expect(annotationDetailsPage.getPrevButton()).toBeVisible();
        }

        if (i === bearAnnotations.length - 1) {
            await expect(annotationDetailsPage.getNextButton()).not.toBeVisible();
        } else {
            await expect(annotationDetailsPage.getNextButton()).toBeVisible();
            await annotationDetailsPage.gotoNextAnnotation();
        }
    }
});

test('user can navigate with stepping navigation with tag', async ({
    annotationsPage,
    annotationDetailsPage
}) => {
    // Select first 3 annotations (from multipleAnnotationsSample).
    await annotationsPage.selectAnnotationByIndex(0);
    await annotationsPage.selectAnnotationByIndex(1);
    await annotationsPage.selectAnnotationByIndex(2);

    const tagName = 'Some annotations' + Math.floor(Math.random() * 1000);

    await annotationsPage.createTag(tagName);

    await annotationsPage.clickTag(tagName);

    await expect(annotationsPage.getAnnotations()).toHaveCount(
        multipleAnnotationsSample.annotations.length
    );

    await annotationsPage.clickAnnotation(0);

    const annotations = multipleAnnotationsSample.annotations;

    // First annotation (cell phone)
    await annotationDetailsPage.verifyDimensions(
        annotations[0].coordinates.width,
        annotations[0].coordinates.height
    );
    await expect(annotationDetailsPage.getPrevButton()).not.toBeVisible();

    await annotationDetailsPage.gotoNextAnnotation();

    // Second annotation (person)
    await annotationDetailsPage.verifyDimensions(
        annotations[1].coordinates.width,
        annotations[1].coordinates.height
    );

    await expect(annotationDetailsPage.getPrevButton()).toBeVisible();
    await annotationDetailsPage.gotoPrevAnnotationByKeyboard();

    // Back to first annotation (cell phone)
    await annotationDetailsPage.verifyDimensions(
        annotations[0].coordinates.width,
        annotations[0].coordinates.height
    );

    await expect(annotationDetailsPage.getNextButton()).toBeVisible();
    await annotationDetailsPage.gotoNextAnnotationByKeyboard();

    // Second annotation again (person)
    await annotationDetailsPage.verifyDimensions(
        annotations[1].coordinates.width,
        annotations[1].coordinates.height
    );

    await annotationDetailsPage.gotoNextAnnotation();

    // Third annotation (handbag)
    await annotationDetailsPage.verifyDimensions(
        annotations[2].coordinates.width,
        annotations[2].coordinates.height
    );
    await expect(annotationDetailsPage.getPrevButton()).toBeVisible();
    await expect(annotationDetailsPage.getNextButton()).not.toBeVisible();
});

test('user can change label of an annotation', async ({
    annotationsPage,
    annotationDetailsPage
}) => {
    await annotationsPage.clickAnnotation(0);

    const originalLabel = cocoDataset.labels.cellPhone.name;
    const newLabel = cocoDataset.labels.apple.name;

    // Verify original label.
    await expect(annotationDetailsPage.getLabel()).toHaveText(originalLabel);
    await expect(annotationDetailsPage.getSvgAnnotationLabel()).toHaveText(originalLabel);

    // Change label to apple.
    await annotationDetailsPage.clickEditLabelButton();
    await annotationDetailsPage.setLabel(newLabel);
    await annotationDetailsPage.clickEditLabelButton();

    // Verify changed label.
    await expect(annotationDetailsPage.getLabel()).toHaveText(newLabel);
    await expect(annotationDetailsPage.getSvgAnnotationLabel()).toHaveText(newLabel);

    // Change back to original label.
    await annotationDetailsPage.clickEditLabelButton();
    await annotationDetailsPage.setLabel(originalLabel);
    await annotationDetailsPage.clickEditLabelButton();

    // Verify restored label.
    await expect(annotationDetailsPage.getLabel()).toHaveText(originalLabel);
    await expect(annotationDetailsPage.getSvgAnnotationLabel()).toHaveText(originalLabel);
});

test('sample details update when navigating between annotations from different samples', async ({
    annotationsPage,
    annotationDetailsPage
}) => {
    // This test specifically verifies that sample details (filename, dimensions, etc.)
    // are properly updated when navigating between annotations that belong to different samples.
    // This was the bug: sample details were not updating during arrow key navigation.

    // Filter by tie label to get annotations from different samples
    await annotationsPage.clickLabel(cocoDataset.labels.tie.name);

    // Start with first annotation from first sample
    await annotationsPage.clickAnnotation(0);

    // Store the initial sample details for comparison
    const initialSampleName = await annotationDetailsPage.getSampleName().textContent();
    const initialSampleWidth = await annotationDetailsPage.getSampleWidth().textContent();
    const initialSampleHeight = await annotationDetailsPage.getSampleHeight().textContent();
    const initialSampleFilepath = await annotationDetailsPage.getSampleFilepath().textContent();

    // Navigate to next annotation (should be from different sample)
    await annotationDetailsPage.waitForNavigation();
    await annotationDetailsPage.gotoNextAnnotationByKeyboard();

    // Wait for the sample name to change (indicating new sample data has loaded)
    await expect(annotationDetailsPage.getSampleName()).not.toHaveText(initialSampleName!);

    // Verify that sample details have changed (different sample)
    const newSampleName = await annotationDetailsPage.getSampleName().textContent();
    const newSampleWidth = await annotationDetailsPage.getSampleWidth().textContent();
    const newSampleHeight = await annotationDetailsPage.getSampleHeight().textContent();
    const newSampleFilepath = await annotationDetailsPage.getSampleFilepath().textContent();

    // Assert that sample details are different (proving we're on a different sample)
    expect(newSampleName).not.toBe(initialSampleName);
    expect(newSampleWidth).not.toBe(initialSampleWidth);
    expect(newSampleHeight).not.toBe(initialSampleHeight);
    expect(newSampleFilepath).not.toBe(initialSampleFilepath);

    // Navigate back to previous annotation
    await annotationDetailsPage.waitForNavigation();
    await annotationDetailsPage.gotoPrevAnnotationByKeyboard();

    // Verify we're back to the original sample with all details restored
    await expect(annotationDetailsPage.getSampleName()).toHaveText(initialSampleName!);
    await expect(annotationDetailsPage.getSampleWidth()).toHaveText(initialSampleWidth!);
    await expect(annotationDetailsPage.getSampleHeight()).toHaveText(initialSampleHeight!);
    await expect(annotationDetailsPage.getSampleFilepath()).toHaveText(initialSampleFilepath!);
});
