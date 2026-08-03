import { expect, test } from '../utils';

test.describe('grid-tag-context-menu', () => {
    test('creates and assigns a tag to a single right-clicked sample', async ({ samplesPage }) => {
        const tagName = `e2e-ctx-${Date.now()}-single`;
        const fileName = await samplesPage.getSampleByIndex(0).getAttribute('data-sample-name');

        await samplesPage.openContextMenuOnSample(0);
        await expect(samplesPage.getContextMenuHeader()).toHaveText(fileName!);

        await samplesPage.openContextMenuTags();
        await samplesPage.createContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        // The new tag shows up in the sidebar tag list.
        await expect(samplesPage.getTagsMenuItem(tagName)).toBeVisible();

        // Re-opening the menu shows it checked for that sample.
        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    test('assigns a tag to the whole selection when right-clicking inside it', async ({
        samplesPage
    }) => {
        const tagName = `e2e-ctx-${Date.now()}-multi`;

        await samplesPage.getSampleByIndex(0).click();
        await samplesPage.getSampleByIndex(1).click();
        await samplesPage.getSampleByIndex(2).click();
        expect(await samplesPage.getNumSelectedSamples()).toBe(3);

        await samplesPage.openContextMenuOnSample(1);
        await expect(samplesPage.getContextMenuHeader()).toHaveText('3 samples');

        await samplesPage.openContextMenuTags();
        await samplesPage.createContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        // Tagging must not disturb the selection.
        expect(await samplesPage.getNumSelectedSamples()).toBe(3);

        // Every selected sample now has the tag, so the row reads checked.
        await samplesPage.openContextMenuOnSample(1);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    test('right-clicking outside the selection targets only that sample', async ({
        samplesPage
    }) => {
        await samplesPage.getSampleByIndex(0).click();
        await samplesPage.getSampleByIndex(1).click();
        expect(await samplesPage.getNumSelectedSamples()).toBe(2);

        const outsideName = await samplesPage.getSampleByIndex(5).getAttribute('data-sample-name');
        await samplesPage.openContextMenuOnSample(5);

        await expect(samplesPage.getContextMenuHeader()).toHaveText(outsideName!);
        await samplesPage.closeContextMenu();
        expect(await samplesPage.getNumSelectedSamples()).toBe(2);
    });

    test('removes a tag from every selected sample', async ({ samplesPage }) => {
        const tagName = `e2e-ctx-${Date.now()}-untag`;

        await samplesPage.getSampleByIndex(0).click();
        await samplesPage.getSampleByIndex(1).click();

        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await samplesPage.createContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        // Clicking the checked row untags the whole selection.
        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'true'
        );
        await samplesPage.toggleContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'false'
        );
    });

    test('shows mixed state when only some selected samples carry the tag', async ({
        samplesPage
    }) => {
        const tagName = `e2e-ctx-${Date.now()}-mixed`;

        // Tag only the first sample.
        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await samplesPage.createContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        await samplesPage.getSampleByIndex(0).click();
        await samplesPage.getSampleByIndex(1).click();

        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'mixed'
        );

        // The first click on a mixed row assigns to all targets.
        await samplesPage.toggleContextMenuTag(tagName);
        await samplesPage.closeContextMenu();

        await samplesPage.openContextMenuOnSample(0);
        await samplesPage.openContextMenuTags();
        await expect(samplesPage.getContextMenuTagRow(tagName)).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    test('closes on Escape and offers clear selection only with a selection', async ({
        samplesPage,
        page
    }) => {
        await samplesPage.openContextMenuOnSample(0);
        await expect(page.getByTestId('grid-context-menu-clear-selection')).toHaveCount(0);
        await samplesPage.closeContextMenu();

        await samplesPage.getSampleByIndex(0).click();
        await samplesPage.getSampleByIndex(1).click();
        await samplesPage.openContextMenuOnSample(0);

        await page.getByTestId('grid-context-menu-clear-selection').click();
        await expect(samplesPage.getContextMenu()).toBeHidden();
        expect(await samplesPage.getNumSelectedSamples()).toBe(0);
    });
});
