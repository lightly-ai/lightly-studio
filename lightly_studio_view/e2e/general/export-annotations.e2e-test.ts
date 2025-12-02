import { expect, test, gotoFirstPage } from '../utils';
import { cocoDataset } from './fixtures';
import fs from 'node:fs/promises';

test.describe('Export Annotations', () => {
    test('Download annotations export JSON', async ({ page }) => {
        await gotoFirstPage(page);

        // Open the Export side panel from the header
        await page.getByRole('button', { name: 'Export' }).click();
        await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();

        // Switch to the "Samples & Annotations" tab and wait until the anchor has the href
        await page.getByRole('tab', { name: 'Samples & Annotations' }).click();
        await expect(page.getByTestId('submit-button')).toHaveAttribute(
            'href',
            /\/api\/datasets\/.*\/export\/annotations\?ts=\d+/
        );

        // Remove target to avoid popup and keep navigation in the same page context
        await page
            .getByTestId('submit-button')
            .evaluate((el: HTMLAnchorElement) => el.removeAttribute('target'));

        // Click and wait for the download event deterministically
        const [download] = await Promise.all([
            page.waitForEvent('download'),
            page.getByTestId('submit-button').click()
        ]);

        // Verify the suggested filename from headers
        expect(download.suggestedFilename()).toBe(cocoDataset.exportFilename);

        // Read downloaded file contents (acceptDownloads is enabled)
        const filePath = await download.path();
        if (!filePath) throw new Error('Download path is undefined');
        const jsonText = await fs.readFile(filePath, 'utf-8');

        // Parse and assert COCO-like structure
        const data = JSON.parse(jsonText);
        expect(Array.isArray(data.images)).toBeTruthy();
        expect(Array.isArray(data.categories)).toBeTruthy();
        expect(Array.isArray(data.annotations)).toBeTruthy();

        // Inspect images
        expect(data.images.length).toBeGreaterThan(0);
        const img = data.images[0];
        expect(img).toHaveProperty('id');
        expect(img).toHaveProperty('file_name');
        expect(img).toHaveProperty('width');
        expect(img).toHaveProperty('height');
        expect(img.file_name).toMatch(/\.jpg$/);

        // Inspect categories
        expect(data.categories.length).toBeGreaterThan(0);
        const cat = data.categories[0];
        expect(cat).toHaveProperty('id');
        expect(cat).toHaveProperty('name');
        expect(cat.name).toBe(cocoDataset.labels.airplane.name);

        // TODO(Michal, 10/2025): Currently we export only object detections, but the test dataset
        // has instance segmentations. Update the test to expect more than 0 annotations later.
        expect(data.annotations.length).toEqual(0);
    });
});
