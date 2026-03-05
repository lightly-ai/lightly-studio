import { Locator } from '@playwright/test';
import { test, expect } from '../../utils';
import { multipleAnnotationsSample, bearSamples, cocoDataset } from '../fixtures';

type BoundingBox = { x: number; y: number; width: number; height: number };

const hasBoxStrokeAtCoordinates = async (canvas: Locator, { x, y, width, height }: BoundingBox) => {
    return await canvas.evaluate(
        (element, box) => {
            const canvasElement = element as HTMLCanvasElement;
            const context = canvasElement.getContext('2d');

            if (!context) {
                return false;
            }

            const maxX = canvasElement.width - 1;
            const maxY = canvasElement.height - 1;

            const hasInkNearPoint = (pointX: number, pointY: number) => {
                for (let deltaX = -1; deltaX <= 1; deltaX++) {
                    for (let deltaY = -1; deltaY <= 1; deltaY++) {
                        const sampleX = Math.min(maxX, Math.max(0, Math.round(pointX + deltaX)));
                        const sampleY = Math.min(maxY, Math.max(0, Math.round(pointY + deltaY)));
                        const alpha = context.getImageData(sampleX, sampleY, 1, 1).data[3];
                        if (alpha > 0) {
                            return true;
                        }
                    }
                }

                return false;
            };

            return [
                [box.x, box.y],
                [box.x + box.width, box.y],
                [box.x, box.y + box.height],
                [box.x + box.width, box.y + box.height]
            ].every(([pointX, pointY]) => hasInkNearPoint(pointX, pointY));
        },
        { x, y, width, height }
    );
};

const expectBoxCoordinates = async (
    canvas: Locator,
    { x, y, width, height }: { x: number; y: number; width: number; height: number }
) => {
    await expect
        .poll(
            async () =>
                hasBoxStrokeAtCoordinates(canvas, {
                    x,
                    y,
                    width,
                    height
                }),
            { timeout: 10000 }
        )
        .toBe(true);
};

test('Annotations should have correct position between annotation label selection', async ({
    samplesPage
}) => {
    await samplesPage.page.addInitScript(() => {
        Object.defineProperty(HTMLCanvasElement.prototype, 'transferControlToOffscreen', {
            configurable: true,
            value: undefined
        });
    });

    await samplesPage.goto();

    // Check that we have the sample without airplane
    await expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).toBeVisible();

    // Check that we have the sample with annotations
    const multipleAnnotationsCanvas = samplesPage
        .getSampleByName(multipleAnnotationsSample.name)
        .locator('canvas')
        .first();
    await expect(multipleAnnotationsCanvas).toBeVisible();
    for (const { coordinates } of multipleAnnotationsSample.annotations) {
        await expectBoxCoordinates(multipleAnnotationsCanvas, coordinates);
    }

    // Select the label "bear"
    const bearLabel = cocoDataset.labels.bear.name;
    expect(bearLabel).toStrictEqual('bear');

    await samplesPage.clickLabel(bearLabel);

    await expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).not.toBeVisible();
    await expect(samplesPage.getSampleByName(bearSamples[1].name)).toBeVisible();

    // Check bear box coordinates
    const bearCanvas = samplesPage.getSampleByName(bearSamples[1].name).locator('canvas').first();
    await expect(bearCanvas).toBeVisible();
    for (let i = 0; i < bearSamples[1].annotations.length; i++) {
        await expectBoxCoordinates(bearCanvas, bearSamples[1].annotations[i].coordinates);
    }

    // Unselect the label "bear"
    await samplesPage.clickLabel(bearLabel);

    // Check that we have the sample without bear again
    await expect(samplesPage.getSampleByName(multipleAnnotationsSample.name)).toBeVisible();
    for (const { coordinates } of multipleAnnotationsSample.annotations) {
        await expectBoxCoordinates(multipleAnnotationsCanvas, coordinates);
    }
});
