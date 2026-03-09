import { expect, test, gotoFirstPage } from '../utils';
import { cocoDataset } from './fixtures';
import fs from 'node:fs/promises';

test.describe('Export Instance Segmentations', () => {
    test('Download instance segmentations export JSON', async ({ page }) => {
        await gotoFirstPage(page);

        // Open the Export side panel from the header
        await page.getByTestId('menu-trigger').click();
        await page.getByTestId('menu-export').click();
        await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();

        // Switch to the correct export type
        await page.getByTestId('export-type-select').click();
        await page.getByRole('option', { name: 'Instance Segmentations' }).click();
        await expect(page.getByTestId('submit-button-instance-segmentations')).toHaveAttribute(
            'href',
            /\/api\/collections\/.*\/export\/annotations\?ts=\d+&annotation_type=instance_segmentation/
        );

        // Remove target to avoid popup and keep navigation in the same page context
        await page
            .getByTestId('submit-button-instance-segmentations')
            .evaluate((el: HTMLAnchorElement) => el.removeAttribute('target'));

        // Click and wait for the download event deterministically
        const [download] = await Promise.all([
            page.waitForEvent('download'),
            page.getByTestId('submit-button-instance-segmentations').click()
        ]);

        // Verify the suggested filename from headers
        expect(download.suggestedFilename()).toBe(cocoDataset.instanceSegmentationExportFilename);

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

        // Inspect annotations
        expect(data.annotations.length).toBeGreaterThan(0);
        const ann = data.annotations[0];
        expect(ann).toHaveProperty('image_id');
        expect(ann).toHaveProperty('category_id');
        expect(ann).toHaveProperty('bbox');
        expect(Array.isArray(ann.bbox));
        expect(ann).toHaveProperty('segmentation');
        // Ensure it's instance segmentation (it can be an array of polygons or RLE)
        expect(
            Array.isArray(ann.segmentation) ||
                (typeof ann.segmentation === 'object' && ann.segmentation !== null)
        ).toBeTruthy();
    });
});
