import { Locator } from '@playwright/test';
import { test, expect } from '../../utils';
import { multipleAnnotationsSample, bearSamples, cocoDataset } from '../fixtures';

type BoundingBox = { x: number; y: number; width: number; height: number };

const getSampleAnnotationCanvas = (sample: Locator) =>
    sample.getByTestId('sample-annotation-item').locator('canvas').first();

const hasBoxStrokeAtCoordinates = async (canvas: Locator, { x, y, width, height }: BoundingBox) => {
    return await canvas.evaluate(
        (element, box) => {
            const canvasElement = element as HTMLCanvasElement;
            const context = canvasElement.getContext('2d', { willReadFrequently: true });

            if (!context) {
                return false;
            }

            const imageData = context.getImageData(
                0,
                0,
                canvasElement.width,
                canvasElement.height
            ).data;
            const canvasWidth = canvasElement.width;
            const maxX = canvasElement.width - 1;
            const maxY = canvasElement.height - 1;
            const minimumAlpha = Math.ceil(0.1 * 255);

            const alphaAt = (pointX: number, pointY: number) => {
                const sampleX = Math.min(maxX, Math.max(0, Math.round(pointX)));
                const sampleY = Math.min(maxY, Math.max(0, Math.round(pointY)));
                return imageData[(sampleY * canvasWidth + sampleX) * 4 + 3];
            };

            const hasInkNearPoint = (
                pointX: number,
                pointY: number,
                radius = 2,
                alphaThreshold = minimumAlpha
            ) => {
                for (let deltaX = -radius; deltaX <= radius; deltaX++) {
                    for (let deltaY = -radius; deltaY <= radius; deltaY++) {
                        const alpha = alphaAt(pointX + deltaX, pointY + deltaY);
                        if (alpha >= alphaThreshold) {
                            return true;
                        }
                    }
                }

                return false;
            };

            const edgeHasInk = (
                fromX: number,
                fromY: number,
                toX: number,
                toY: number,
                outwardNormalX: number,
                outwardNormalY: number
            ) => {
                const distance = Math.hypot(toX - fromX, toY - fromY);
                const sampleCount = Math.max(8, Math.ceil(distance / 4));
                const endpointRadius = 2;

                const endpointHasStroke = (pointX: number, pointY: number) =>
                    hasInkNearPoint(pointX, pointY, endpointRadius) &&
                    hasInkNearPoint(
                        pointX + outwardNormalX,
                        pointY + outwardNormalY,
                        endpointRadius
                    );

                if (!endpointHasStroke(fromX, fromY) || !endpointHasStroke(toX, toY)) {
                    return false;
                }

                let hits = 0;
                let consecutiveHits = 0;
                let maxConsecutiveHits = 0;

                for (let i = 0; i <= sampleCount; i++) {
                    const t = i / sampleCount;
                    const pointX = fromX + (toX - fromX) * t;
                    const pointY = fromY + (toY - fromY) * t;
                    const hasEdgeInk = hasInkNearPoint(pointX, pointY, 1);
                    const hasOuterInk = hasInkNearPoint(
                        pointX + outwardNormalX,
                        pointY + outwardNormalY,
                        1
                    );

                    if (hasEdgeInk && hasOuterInk) {
                        hits++;
                        consecutiveHits++;
                        maxConsecutiveHits = Math.max(maxConsecutiveHits, consecutiveHits);
                    } else {
                        consecutiveHits = 0;
                    }
                }

                const totalSamples = sampleCount + 1;
                const minimumHitCount = Math.ceil(totalSamples * 0.7);
                const minimumConsecutiveHits = Math.max(5, Math.ceil(totalSamples * 0.3));

                return hits >= minimumHitCount && maxConsecutiveHits >= minimumConsecutiveHits;
            };

            const left = box.x;
            const right = box.x + box.width;
            const top = box.y;
            const bottom = box.y + box.height;

            return (
                edgeHasInk(left, top, right, top, 0, -1) &&
                edgeHasInk(left, bottom, right, bottom, 0, 1) &&
                edgeHasInk(left, top, left, bottom, -1, 0) &&
                edgeHasInk(right, top, right, bottom, 1, 0)
            );
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
            // todo leave a comment if this works
            { timeout: 20000 }
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
    const multipleAnnotationsCanvas = getSampleAnnotationCanvas(
        samplesPage.getSampleByName(multipleAnnotationsSample.name)
    );
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
    const bearCanvas = getSampleAnnotationCanvas(samplesPage.getSampleByName(bearSamples[1].name));
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
