import { expect, test, pressButton } from '../utils';
import { cocoDataset } from './fixtures';

test('Shift+click adds the full range in image grid', async ({ samplesPage }) => {
    await samplesPage.getSampleByIndex(1).click();
    expect(await samplesPage.getNumSelectedSamples()).toBe(1);

    await samplesPage.getSampleByIndex(7).click({
        modifiers: ['Shift']
    });
    expect(await samplesPage.getNumSelectedSamples()).toBe(7);
});

test('selection is cleared when switching from samples view and back', async ({
    page,
    samplesPage
}) => {
    await samplesPage.getSampleByIndex(0).click();
    await samplesPage.getSampleByIndex(1).click();
    expect(await samplesPage.getNumSelectedSamples()).toBe(2);

    await page.getByTestId('navigation-menu-annotations').click();
    await expect(page.getByTestId('annotation-grid-item').first()).toBeVisible({ timeout: 10000 });

    await page.getByTestId('navigation-menu-images').click();
    await expect(samplesPage.getSamples().first()).toBeVisible({ timeout: 10000 });
    expect(await samplesPage.getNumSelectedSamples()).toBe(0);
});

test('Label filtering shows distinct samples only', async ({ samplesPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Filter by "book" label.
    await samplesPage.clickLabel(cocoDataset.labels.book.name);

    // There are 3 samples: 2 with a single "book" annotation and 1 with 4 "book" annotations.
    // UI should show only distinct samples (e.g. 3 samples instead of 6).
    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(cocoDataset.labels.book.sampleCount);
});

test('Tag filtering shows distinct samples only', async ({ page, samplesPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Generate unique tag names to avoid conflicts on subsequent test runs.
    const timestamp = Date.now();
    const tag1Name = `tag_1_2_3_${timestamp}`;
    const tag2Name = `tag_3_4_5_${timestamp}`;

    // Select first 3 samples.
    const selectBoxes = page.getByTestId('sample-selected-box');
    for (let i = 0; i < 3; i++) {
        await selectBoxes.nth(i).click();
    }
    expect(await samplesPage.getNumSelectedSamples()).toBe(3);

    // Create first tag.
    await samplesPage.createTag(tag1Name);

    // Select next samples.
    for (let i = 2; i < 5; i++) {
        await selectBoxes.nth(i).click();
    }
    expect(await samplesPage.getNumSelectedSamples()).toBe(3);

    // Create second tag.
    await samplesPage.createTag(tag2Name);

    // Filter by both tags - should show 5 distinct samples (1,2,3,4,5), not 6.
    await samplesPage.pressTag(tag1Name);
    await samplesPage.pressTag(tag2Name);

    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(5);
});

test('Diversity selection creates tag with correct number of samples', async ({
    page,
    samplesPage
}) => {
    // samplesPage fixture automatically navigates and loads samples

    // Generate unique tag name to avoid conflicts.
    const timestamp = Date.now();
    const selectionTagName = `diversity_selection_${timestamp}`;
    const nSamples = 10;

    // Create diversity selection.
    await samplesPage.createDiversitySelection(nSamples, selectionTagName);

    // Verify success toast appears.
    await expect(page.getByText('Selection created successfully')).toBeVisible({ timeout: 10000 });

    // Verify the new tag appears in the tags list.
    const tagNames = await samplesPage.getTagNames();
    expect(tagNames).toContain(selectionTagName);

    // Filter by the new tag and verify the correct number of samples.
    await samplesPage.pressTag(selectionTagName);
    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(nSamples);
});

test('Typicality selection creates tag with correct number of samples', async ({
    page,
    samplesPage
}) => {
    // samplesPage fixture automatically navigates and loads samples

    // Generate unique tag name to avoid conflicts.
    const timestamp = Date.now();
    const selectionTagName = `typicality_selection_${timestamp}`;
    const nSamples = 10;

    // Setup API response listeners to validate the two-step flow.
    const typicalityPromise = page.waitForResponse(
        (response) => response.url().includes('/metadata/typicality') && response.status() === 204
    );
    const selectionPromise = page.waitForResponse(
        (response) => response.url().includes('/selection') && response.status() === 204
    );

    // Create typicality selection.
    await samplesPage.createTypicalitySelection(nSamples, selectionTagName);

    // Verify both API calls happened in sequence.
    await typicalityPromise;
    await selectionPromise;

    // Verify success toast appears.
    await expect(page.getByText('Selection created successfully')).toBeVisible({ timeout: 10000 });

    // Verify the new tag appears in the tags list.
    const tagNames = await samplesPage.getTagNames();
    expect(tagNames).toContain(selectionTagName);

    // Filter by the new tag and verify the correct number of samples.
    await samplesPage.pressTag(selectionTagName);
    const sampleCount = await samplesPage.getSamples().count();
    expect(sampleCount).toBe(nSamples);
});

test('Selection shows error toast when tag already exists', async ({ page, samplesPage }) => {
    // samplesPage fixture automatically navigates and loads samples

    // Generate unique tag name to avoid conflicts.
    const timestamp = Date.now();
    const duplicateTagName = `duplicate_tag_${timestamp}`;
    const nSamples = 5;

    // Create the tag once (using diversity).
    await samplesPage.createDiversitySelection(nSamples, duplicateTagName);

    // Wait for success toast.
    await expect(page.getByText('Selection created successfully')).toBeVisible({ timeout: 10000 });

    // Verify the new tag appears in the tags list.
    const tagNames = await samplesPage.getTagNames();
    expect(tagNames).toContain(duplicateTagName);

    // Test that both strategies reject duplicate tag names.
    const strategies = ['diversity', 'typicality'] as const;

    for (const strategy of strategies) {
        // Try to create selection with the duplicate tag name.
        await samplesPage.createSelection(strategy, nSamples, duplicateTagName);

        // Verify error toast appears with tag name in message.
        await expect(
            page.getByText(`Tag with name ${duplicateTagName} already exists`)
        ).toBeVisible({ timeout: 10000 });

        // Close the selection dialog to reset for the next iteration.
        await pressButton(page, 'selection-dialog-cancel');
    }
});
