import { expect, test, gotoFirstPage } from '../utils';
import { cocoDataset } from './fixtures';
import fs from 'node:fs/promises';

test.describe('Export Instance Segmentations', () => {
    test('Prepare a test instance segmentation in sample details', async ({
        samplesPage,
        sampleDetailsPage
    }) => {
        // Double-click on the first sample to navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Start edit mode
        await sampleDetailsPage.clickEditButton();

        // Select the brush tool
        await sampleDetailsPage.page.getByTestId('brush-tool-button').click();

        // Draw a small square mask in the middle of the image
        // We assume the image is visible and the brush tool is active.
        // The coordinates are relative to the viewport, but the brush tool
        // handles the translation to image coordinates.
        const box = await sampleDetailsPage.page.getByTestId('zoomable-container').boundingBox();
        if (!box) throw new Error('Zoomable container not found');

        const centerX = box.x + box.width / 2;
        const centerY = box.y + box.height / 2;

        const responsePromise = sampleDetailsPage.page.waitForResponse(
            (response) =>
                response.request().method() === 'POST' &&
                response.url().includes('/annotations') &&
                response.status() === 201
        );

        await sampleDetailsPage.page.mouse.move(centerX, centerY);
        await sampleDetailsPage.page.mouse.down();
        await sampleDetailsPage.page.mouse.move(centerX + 20, centerY + 20);
        await sampleDetailsPage.page.mouse.up();

        // Wait for the annotation to be created
        await responsePromise;

        // Set a specific label for the new annotation
        await sampleDetailsPage.setFirstAnnotationLabel('test-label');
    });

    test('Download instance segmentations export JSON', async ({ page }) => {
        await gotoFirstPage(page);

        // Open the Export side panel from the header
        await page.getByTestId('menu-trigger').click();
        await page.getByTestId('menu-export').click();
        await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();

        // Switch to the correct tab and wait until the anchor has the href
        await page.getByRole('tab', { name: 'Instance Segmentations' }).click();
        await expect(page.getByTestId('submit-button-instance-segmentations')).toHaveAttribute(
            'href',
            /\/api\/collections\/.*\/export\/instance-segmentations\?ts=\d+/
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
        // There should be a category with the name we added
        const cat = data.categories.find((c: any) => c.name === 'test-label');
        expect(cat).toBeDefined();

        // The test collection has instance segmentations
        expect(data.annotations.length).toBeGreaterThan(0);
        const ann = data.annotations.find((a: any) => a.category_id === cat.id);
        expect(ann).toBeDefined();
        expect(ann).toHaveProperty('id');
        expect(ann).toHaveProperty('image_id');
        expect(ann).toHaveProperty('category_id');
        expect(ann).toHaveProperty('segmentation');
        expect(ann).toHaveProperty('area');
        expect(ann).toHaveProperty('iscrowd');
    });

    test('Clean up', async ({ samplesPage, sampleDetailsPage, annotationDetailsPage }) => {
        // Navigate to sample details
        await samplesPage.doubleClickFirstSample();
        await sampleDetailsPage.pageIsReady();

        // Navigate to the annotation we created
        // (It should be the first one as it was recently created or we can find it by label)
        await sampleDetailsPage.getAnnotationBoxByLabel('test-label').click();

        // Start edit mode and delete the annotation
        await sampleDetailsPage.clickEditButton();
        await annotationDetailsPage.getAnnotationDeleteButton().click();
        await annotationDetailsPage.getAnnotationConfirmDeleteButton().click();

        // Wait for the deletion to be persisted
        await sampleDetailsPage.page.waitForResponse(
            (response) =>
                response.request().method() === 'DELETE' &&
                response.url().includes('/annotations') &&
                response.status() === 200
        );

        // Check that the annotation is gone
        await expect(sampleDetailsPage.getAnnotationBoxByLabel('test-label')).not.toBeVisible();
    });
});
