import { describe, expect, it, vi } from 'vitest';
import {
    computeStroke,
    drawBoxesOnContext,
    drawPolygonsOnContext,
    renderMasks,
    type BoundingBoxInput,
    type PolygonInput
} from './maskRendererUtils';

describe('maskRendererUtils', () => {
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

    it('draws valid polygons and skips invalid ones', () => {
        const ctx = {
            save: vi.fn(),
            restore: vi.fn(),
            beginPath: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            closePath: vi.fn(),
            fill: vi.fn(),
            stroke: vi.fn(),
            lineWidth: 0,
            fillStyle: '',
            strokeStyle: ''
        } as unknown as OffscreenCanvasRenderingContext2D;

        const polygons: PolygonInput[] = [
            {
                points: [
                    [0, 0],
                    [2, 0]
                ],
                strokeColor: [0, 0, 0, 255],
                fillColor: [0, 0, 0, 64]
            },
            {
                points: [
                    [1, 1],
                    [4, 1],
                    [2, 3]
                ],
                strokeColor: [255, 0, 0, 255],
                fillColor: [255, 0, 0, 64]
            }
        ];

        drawPolygonsOnContext(ctx, polygons, 3);

        expect(ctx.beginPath).toHaveBeenCalledTimes(1);
        expect(ctx.moveTo).toHaveBeenCalledWith(1, 1);
        expect(ctx.lineTo).toHaveBeenCalledWith(4, 1);
        expect(ctx.lineTo).toHaveBeenCalledWith(2, 3);
        expect(ctx.closePath).toHaveBeenCalledTimes(1);
        expect(ctx.fill).toHaveBeenCalledTimes(1);
        expect(ctx.stroke).toHaveBeenCalledTimes(1);
        expect(ctx.lineWidth).toBe(3);
    });
});
