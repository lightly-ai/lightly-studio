import { describe, expect, it, vi } from 'vitest';
import { createBrushDrawer } from './brushDrawer';

type Mock2dContext = {
    fillRect: ReturnType<typeof vi.fn>;
    globalCompositeOperation: string;
    fillStyle: string;
};

describe('createBrushDrawer', () => {
    it('fills the exact pixels of a size 2 dot', () => {
        const context: Mock2dContext = {
            fillRect: vi.fn(),
            globalCompositeOperation: 'destination-over',
            fillStyle: 'transparent'
        };

        const ensureSourceMaskContext = vi.fn(() => context as unknown as CanvasRenderingContext2D);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushDot({
            point: { x: 3.7, y: 5.2 },
            brushSize: 2,
            width: 100,
            height: 50
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledWith(100, 50);
        expect(context.fillRect.mock.calls).toEqual([
            [3, 4, 2, 1],
            [3, 5, 2, 1]
        ]);
        expect(context.globalCompositeOperation).toBe('source-over');
        expect(context.fillStyle).toBe('black');
    });

    it('fills every pixel along a size 1 line', () => {
        const context: Mock2dContext = {
            fillRect: vi.fn(),
            globalCompositeOperation: 'source-over',
            fillStyle: 'transparent'
        };

        const ensureSourceMaskContext = vi.fn(() => context as unknown as CanvasRenderingContext2D);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushLine({
            from: { x: 0.5, y: 0.5 },
            to: { x: 3.5, y: 0.5 },
            brushSize: 1,
            width: 100,
            height: 50,
            compositeOperation: 'destination-out'
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledWith(100, 50);
        expect(context.fillRect.mock.calls).toEqual([
            [0, 0, 1, 1],
            [1, 0, 1, 1],
            [2, 0, 1, 1],
            [3, 0, 1, 1]
        ]);
        expect(context.globalCompositeOperation).toBe('destination-out');
        expect(context.fillStyle).toBe('black');
    });

    it('does nothing when source context is unavailable', () => {
        const ensureSourceMaskContext = vi.fn(() => null);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushDot({
            point: { x: 0, y: 0 },
            brushSize: 2,
            width: 10,
            height: 10
        });

        brushDrawer.drawBrushLine({
            from: { x: 0, y: 0 },
            to: { x: 1, y: 1 },
            brushSize: 2,
            width: 10,
            height: 10
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledTimes(2);
    });
});
