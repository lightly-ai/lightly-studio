import { expect, test } from '../../utils';
import type { Page } from '@playwright/test';
import { cocoDataset } from '../fixtures';

const getCurrentSampleIdFromUrl = (page: Page): string => {
    const match = page.url().match(/\/samples\/([^/]+)$/);
    if (!match?.[1]) {
        throw new Error(`Could not parse sample id from URL: ${page.url()}`);
    }
    return match[1];
};

const getCollectionIdFromUrl = (page: Page): string => {
    const match = page.url().match(/\/datasets\/[^/]+\/[^/]+\/([^/]+)\/samples/);
    if (!match?.[1]) {
        throw new Error(`Could not parse collection id from URL: ${page.url()}`);
    }
    return match[1];
};

const drawSmallBrushStrokeAndGetTargetSampleId = async (page: Page): Promise<string> => {
    const createAnnotationRequestPromise = page.waitForRequest(
        (request) =>
            request.method() === 'POST' &&
            request.url().includes('/annotations') &&
            !!request.postData()
    );

    const drawingArea = page.locator('rect[role="button"][style*="cursor: crosshair"]').first();
    await expect(drawingArea).toBeVisible();

    const box = await drawingArea.boundingBox();
    if (!box) {
        throw new Error('Could not determine drawing area bounds');
    }

    const startX = box.x + box.width * 0.35;
    const startY = box.y + box.height * 0.35;

    await page.mouse.move(startX, startY);
    await page.mouse.down();
    await page.mouse.move(startX + 20, startY + 15);
    await page.mouse.up();

    const createAnnotationRequest = await createAnnotationRequestPromise;
    const body = createAnnotationRequest.postDataJSON() as { parent_sample_id?: string };

    if (!body.parent_sample_id) {
        throw new Error('Create annotation request has no parent_sample_id');
    }

    return body.parent_sample_id;
};

const assertBrushIsVisuallySelected = async (page: Page) => {
    await expect(page.getByRole('button', { name: 'Instance Segmentation Brush' })).toHaveClass(
        /bg-black\/40/
    );
};

test('brush stays effective across keyboard navigation while creating masks on 3 samples', async ({
    page,
    samplesPage,
    sampleDetailsPage
}) => {
    // Do not persist new annotations in shared E2E dataset.
    await page.route('**/annotations', async (route) => {
        const request = route.request();
        if (request.method() !== 'POST') {
            await route.continue();
            return;
        }

        const body = request.postDataJSON() as { parent_sample_id?: string };
        const parentSampleId = body.parent_sample_id ?? 'unknown-sample';
        const now = Date.now().toString();
        await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
                sample_id: `stub-${parentSampleId}-${now}`,
                parent_sample_id: parentSampleId,
                annotation_type: 'instance_segmentation',
                annotation_label: {
                    annotation_label_id: 'stub-label-id',
                    annotation_label_name: cocoDataset.labels.person.name
                },
                bounding_box: { x: 0, y: 0, width: 1, height: 1 },
                segmentation_details: {
                    segmentation_mask: {
                        counts: [1],
                        size: [1, 1]
                    }
                }
            })
        });
    });

    await samplesPage.doubleClickFirstSample();
    await sampleDetailsPage.pageIsReady();
    const collectionId = getCollectionIdFromUrl(page);
    await page.evaluate(
        ({ key, collectionId, labelName }) => {
            const raw = sessionStorage.getItem(key);
            const value = raw ? JSON.parse(raw) : {};
            value[collectionId] = labelName;
            sessionStorage.setItem(key, JSON.stringify(value));
        },
        {
            key: 'lightlyStudio_last_annotation_label',
            collectionId,
            labelName: cocoDataset.labels.person.name
        }
    );

    await sampleDetailsPage.clickEditButton();

    const brushButton = page.getByRole('button', { name: 'Instance Segmentation Brush' });
    await brushButton.click();

    await assertBrushIsVisuallySelected(page);

    for (let sampleNumber = 1; sampleNumber <= 3; sampleNumber++) {
        const currentSampleId = getCurrentSampleIdFromUrl(page);
        const requestTargetSampleId = await drawSmallBrushStrokeAndGetTargetSampleId(page);

        expect(requestTargetSampleId).toBe(currentSampleId);

        if (sampleNumber < 3) {
            await sampleDetailsPage.gotoNextSampleByKeyboard();
            await expect(page.getByTestId('sample-details-breadcrumb')).toContainText(
                `Sample ${sampleNumber + 1} of`
            );
            await assertBrushIsVisuallySelected(page);
        }
    }
});
