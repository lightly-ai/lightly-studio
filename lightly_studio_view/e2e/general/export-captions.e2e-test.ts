import { expect, test, gotoFirstPage } from '../utils';
import { cocoDataset } from './fixtures';
import fs from 'node:fs/promises';

test.describe('Export Captions', () => {
    test('Prepare a test caption in sample details', async ({ samplesPage, sampleDetailsPage }) => {
        // Double-click on the first sample to navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Initially there are no captions
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(0);

        // Start edit mode and add a caption
        await sampleDetailsPage.clickEditButton();
        await sampleDetailsPage.addCaption();
        await sampleDetailsPage.updateNthCaption(0, 'test caption');

        // Check a caption was added
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(1);
    });
    test('Download captions export JSON', async ({ page }) => {
        await gotoFirstPage(page);

        // Open the Export side panel from the header
        await page.getByTestId('menu-trigger').click();
        await page.getByTestId('menu-export').click();
        await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();

        // Switch to the correct tab and wait until the anchor has the href
        await page.getByRole('tab', { name: 'Image Captions' }).click();
        await expect(page.getByTestId('submit-button-captions')).toHaveAttribute(
            'href',
            /\/api\/datasets\/.*\/export\/captions\?ts=\d+/
        );

        // Remove target to avoid popup and keep navigation in the same page context
        await page
            .getByTestId('submit-button-captions')
            .evaluate((el: HTMLAnchorElement) => el.removeAttribute('target'));

        // Click and wait for the download event deterministically
        const [download] = await Promise.all([
            page.waitForEvent('download'),
            page.getByTestId('submit-button-captions').click()
        ]);

        // Verify the suggested filename from headers
        expect(download.suggestedFilename()).toBe(cocoDataset.captionExportFilename);

        // Read downloaded file contents (acceptDownloads is enabled)
        const filePath = await download.path();
        if (!filePath) throw new Error('Download path is undefined');
        const jsonText = await fs.readFile(filePath, 'utf-8');

        // Parse and assert COCO-like structure
        const data = JSON.parse(jsonText);
        expect(Array.isArray(data.images)).toBeTruthy();
        expect(Array.isArray(data.annotations)).toBeTruthy();

        // Inspect images
        expect(data.images.length).toBeGreaterThan(0);
        const img = data.images[0];
        expect(img).toHaveProperty('id');
        expect(img).toHaveProperty('file_name');
        expect(img).toHaveProperty('width');
        expect(img).toHaveProperty('height');
        expect(img.file_name).toMatch(/\.jpg$/);

        // Inspect annotations
        // There should be exactly one caption with the text we added
        expect(data.annotations.length).toEqual(1);
        const ann = data.annotations[0];
        expect(ann).toHaveProperty('id');
        expect(ann).toHaveProperty('image_id');
        expect(ann.caption).toEqual('test caption');
    });
    test('Clean up', async ({ samplesPage, sampleDetailsPage }) => {
        // Navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Start edit mode and delete the remaining caption
        await sampleDetailsPage.clickEditButton();
        await sampleDetailsPage.deleteNthCaption(0);

        // Check that there are no captions left
        expect(await sampleDetailsPage.getCaptionCount()).toEqual(0);
    });
});
