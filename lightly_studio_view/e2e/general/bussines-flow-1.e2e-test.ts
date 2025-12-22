import { expect, test } from '../utils';
import { cocoDataset } from './fixtures';

test.describe('bussines-flow1', () => {
    // Shared tag name for cats tests - generated once per test run
    const catsTagName = `cats_${Date.now()}`;

    test('User Opens UI', async ({ page, samplesPage }) => {
        // samplesPage fixture automatically navigates and loads samples

        // Expect first page of samples to be loaded (default page size from COCO collection)
        expect(await samplesPage.getSamples().count()).toBe(cocoDataset.defaultPageSize);

        // Check if we have some annotations on screen.
        const annotationCount = await page.getByTestId('annotation_box').count();
        expect(annotationCount).toBeGreaterThan(0);

        // No images in the grid view should be selected
        expect(await samplesPage.getNumSelectedSamples()).toBe(0);
    });

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    test('Toggle Annotations', async ({ page, samplesPage }) => {
        // samplesPage fixture automatically navigates and loads samples

        await page.keyboard.down('v');
        await page.waitForTimeout(100);

        // Check that annotation boxes are not visible anymore.
        const annotations = page.getByTestId('annotation_box');
        const annotationsCount = await annotations.count();
        for (let i = 0; i < annotationsCount; i++) {
            expect(annotations.nth(i)).toBeHidden();
        }
        await page.waitForTimeout(100);
        await page.keyboard.up('v');
    });

    // TODO(Michal, 12/2025): The test is flakey, needs investigation.
    test('Create cats tag', async ({ page, samplesPage, sampleDetailsPage }) => {
        // samplesPage fixture automatically navigates and loads samples
        // Uses shared catsTagName declared at describe level

        // Search for "cats" using embedding search
        await samplesPage.textSearch('cats');

        // Click on the first sample
        await samplesPage.doubleClickFirstSample();

        // Wait for sample details to load
        await expect(page.getByTestId('sample-details')).toBeVisible();
        await expect(page.getByTestId('sample-details-breadcrumb')).toBeVisible();
        await expect(page.getByText(`Sample 1 of ${cocoDataset.totalSamples}`)).toBeVisible();

        // There should be three individual annotations: two "cat" and one "chair"
        const sampleAnnotationNames = page.getByTestId('sample-details-pannel-annotation-name');
        expect(await sampleAnnotationNames.count()).toBe(3);

        // Collect all annotation names
        const annotationNames = [];
        for (let i = 0; i < 3; i++) {
            const name = await sampleAnnotationNames.nth(i).textContent();
            annotationNames.push(name);
        }

        // Verify we have exactly 2 "cat" annotations and 1 "chair" annotation
        const catCount = annotationNames.filter(
            (name) => name === cocoDataset.labels.cat.name
        ).length;
        const chairCount = annotationNames.filter(
            (name) => name === cocoDataset.labels.chair.name
        ).length;
        expect(catCount).toBe(2);
        expect(chairCount).toBe(1);

        // Verify annotations are sorted alphabetically (cat, cat, chair)
        expect(annotationNames[0]).toBe(cocoDataset.labels.cat.name);
        expect(annotationNames[1]).toBe(cocoDataset.labels.cat.name);
        expect(annotationNames[2]).toBe(cocoDataset.labels.chair.name);

        const selectBoxes = page.getByTestId('sample-selected-box');
        const selectBoxeCount = await selectBoxes.count();
        expect(selectBoxeCount).toBe(1);
        await selectBoxes.click();
        await page.waitForTimeout(100);

        await page.getByTestId('navigation-menu-images').click();

        await expect(samplesPage.getSamples().first()).toBeVisible({ timeout: 10000 });
        const selectedSamples = await samplesPage.getNumSelectedSamples();
        expect(selectedSamples).toBe(1);

        // Create the tag with unique name
        await samplesPage.createTag(catsTagName);
        expect(samplesPage.getTagsMenuItem(catsTagName)).toBeDefined();

        // Filter by the newly created tag
        await samplesPage.pressTag(catsTagName);
        expect(await samplesPage.getSamples().count()).toBe(1);

        // Clear tag filter to see all samples again
        await samplesPage.pressTag(catsTagName);
        expect(await samplesPage.getSamples().count()).toBe(cocoDataset.defaultPageSize);

        // Clear the search input by typing empty string and pressing Enter.
        // The first sample should be the default one.
        await samplesPage.textSearch('');
        await samplesPage.doubleClickFirstSample();
        expect(await sampleDetailsPage.getSampleName()).toHaveText(cocoDataset.firstSampleName);
    });

    test('Selections persist across filtering including samples beyond visible page', async ({
        page,
        samplesPage
    }) => {
        // samplesPage fixture automatically navigates and loads samples

        const dogsTagName = `dogs_${Date.now()}`;

        // Filter by dog label to see all 5 dog samples together.
        await samplesPage.clickLabel(cocoDataset.labels.dog.name);
        expect(await samplesPage.getSamples().count()).toBe(cocoDataset.labels.dog.sampleCount);

        // Select all dog samples.
        const selectBoxes = page.getByTestId('sample-selected-box');
        for (let i = 0; i < cocoDataset.labels.dog.sampleCount; i++) {
            await selectBoxes.nth(i).click();
            await page.waitForTimeout(10);
        }
        expect(await samplesPage.getNumSelectedSamples()).toBe(cocoDataset.labels.dog.sampleCount);

        // Unfilter by clicking dog label again.
        // 2 of the 5 selected dogs are beyond the first 100 samples -> not visible
        await samplesPage.clickLabel(cocoDataset.labels.dog.name);
        expect(await samplesPage.getSamples().count()).toBe(cocoDataset.defaultPageSize);

        // Create tag to verify all 5 selections persisted (including those not visible).
        await samplesPage.createTag(dogsTagName);
        await samplesPage.goto();

        expect(samplesPage.getTagsMenuItem(dogsTagName)).toBeDefined();

        // Filter by tag - should show all 5 dog samples.
        await samplesPage.pressTag(dogsTagName);
        expect(await samplesPage.getSamples().count()).toBe(cocoDataset.labels.dog.sampleCount);
    });
});
