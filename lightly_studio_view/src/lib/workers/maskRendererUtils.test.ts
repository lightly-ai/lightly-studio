import { describe, expect, it, vi } from 'vitest';
import {
    computeStroke,
    decodeRLEToBinaryMask,
    drawBoxesOnContext,
    renderMasks,
    type BoundingBoxInput
} from './maskRendererUtils';

describe('maskRendererUtils', () => {
    it('decodes RLE into binary mask', () => {
        const mask = decodeRLEToBinaryMask([2, 2], 2, 2);
        expect([...mask]).toEqual([0, 0, 1, 1]);
    });

    it('renders masks into RGBA pixels', () => {
        const color: BoundingBoxInput['color'] = [10, 20, 30, 40];
        const pixels = renderMasks(2, 2, [{ rle: [1, 3], color }]);
        const expected = new Uint8ClampedArray([0, 0, 0, 0, ...color, ...color, ...color]);
        expect(pixels).toEqual(expected);
    });

    it('clamps boxes before drawing', () => {
        const ctx = {
            save: vi.fn(),
            restore: vi.fn(),
            strokeRect: vi.fn(),
            lineWidth: 0,
            strokeStyle: ''
        } as unknown as OffscreenCanvasRenderingContext2D;

        const boxes: BoundingBoxInput[] = [
            { x: -1, y: -1, width: 3, height: 10, color: [0, 0, 0, 255] }
        ];

        drawBoxesOnContext(ctx, boxes, 5, 4, 2);

        expect(ctx.save).toHaveBeenCalledTimes(1);
        expect(ctx.restore).toHaveBeenCalledTimes(1);
        expect(ctx.lineWidth).toBe(2);
        expect(ctx.strokeStyle).toBe('rgba(0, 0, 0, 1)');
        expect(ctx.strokeRect).toHaveBeenCalledWith(0, 0, 3, 4);
    });

    it('computes stroke inversely to scale', () => {
        expect(computeStroke(2, 1)).toBeCloseTo(1);
        expect(computeStroke()).toBeCloseTo(2);
    });
});
