import { describe, expect, it, vi } from 'vitest';
import {
    drawBoxesOnContext,
    getRenderTransform,
    renderMasks,
    transformBoxes,
    type BoundingBoxInput
} from './maskRendererUtils';
import { createRenderGeometry as geometry } from './maskRenderer.testFixtures';

describe('maskRendererUtils', () => {
    it('renders a large logical mask into only the output-sized RGBA buffer', () => {
        const pixels = renderMasks(geometry({ sourceWidth: 20_000, sourceHeight: 20_000 }), [
            { rle: [0, 400_000_000], color: [10, 20, 30, 40] }
        ]);

        expect(pixels.byteLength).toBe(200 * 200 * 4);
        expect(pixels.slice(0, 4)).toEqual(new Uint8ClampedArray([10, 20, 30, 40]));
    });

    it('leaves pixels beyond a partial RLE transparent', () => {
        const pixels = renderMasks(
            geometry({ sourceWidth: 4, sourceHeight: 1, outputWidth: 4, outputHeight: 1 }),
            [{ rle: [0, 2], color: [10, 20, 30, 40] }]
        );

        expect(pixels).toEqual(
            new Uint8ClampedArray([10, 20, 30, 40, 10, 20, 30, 40, 0, 0, 0, 0, 0, 0, 0, 0])
        );
    });

    it.each([
        {
            name: 'contain landscape',
            input: geometry({ sourceWidth: 200, sourceHeight: 100 }),
            expected: { scale: 1, offsetX: 0, offsetY: 50 }
        },
        {
            name: 'contain portrait',
            input: geometry({ sourceWidth: 100, sourceHeight: 200 }),
            expected: { scale: 1, offsetX: 50, offsetY: 0 }
        },
        {
            name: 'cover landscape',
            input: geometry({ sourceWidth: 200, sourceHeight: 100, objectFit: 'cover' }),
            expected: { scale: 2, offsetX: -100, offsetY: 0 }
        },
        {
            name: 'cover portrait',
            input: geometry({ sourceWidth: 100, sourceHeight: 200, objectFit: 'cover' }),
            expected: { scale: 2, offsetX: 0, offsetY: -100 }
        },
        {
            name: 'annotation crop',
            input: geometry({
                sourceWidth: 1000,
                sourceHeight: 800,
                outputWidth: 200,
                outputHeight: 100,
                sourceCrop: { x: 100, y: 200, width: 400, height: 200 }
            }),
            expected: { scale: 0.5, offsetX: -50, offsetY: -100 }
        }
    ])('computes the $name transform', ({ input, expected }) => {
        expect(getRenderTransform(input)).toMatchObject(expected);
    });

    it('transforms and clips boxes into output coordinates', () => {
        const boxes: BoundingBoxInput[] = [
            { x: -10, y: 10, width: 30, height: 40, color: [0, 0, 0, 255] }
        ];

        expect(transformBoxes(geometry(), boxes)).toEqual([
            { x: 0, y: 20, width: 40, height: 80, color: [0, 0, 0, 255] }
        ]);
    });

    it('clips boxes to the source crop before applying contain letterboxing', () => {
        const boxes: BoundingBoxInput[] = [
            { x: 0, y: 0, width: 100, height: 100, color: [0, 0, 0, 255] }
        ];

        expect(
            transformBoxes(geometry({ sourceCrop: { x: 25, y: 25, width: 50, height: 25 } }), boxes)
        ).toEqual([{ x: 0, y: 50, width: 200, height: 100, color: [0, 0, 0, 255] }]);
    });

    it('draws transformed boxes with a tile-sized stroke', () => {
        const ctx = {
            save: vi.fn(),
            restore: vi.fn(),
            strokeRect: vi.fn(),
            lineWidth: 0,
            strokeStyle: ''
        } as unknown as OffscreenCanvasRenderingContext2D;
        const boxes: BoundingBoxInput[] = [
            { x: 1, y: 2, width: 3, height: 4, color: [0, 0, 0, 255] }
        ];

        drawBoxesOnContext(ctx, boxes);

        expect(ctx.lineWidth).toBe(2);
        expect(ctx.strokeStyle).toBe('rgba(0, 0, 0, 1)');
        expect(ctx.strokeRect).toHaveBeenCalledWith(1, 2, 3, 4);
    });
});
