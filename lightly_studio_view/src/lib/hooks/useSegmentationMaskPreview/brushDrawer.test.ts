import { describe, expect, it, vi } from 'vitest';
import { createBrushDrawer } from './brushDrawer';

type Mock2dContext = {
    beginPath: ReturnType<typeof vi.fn>;
    arc: ReturnType<typeof vi.fn>;
    fill: ReturnType<typeof vi.fn>;
    moveTo: ReturnType<typeof vi.fn>;
    lineTo: ReturnType<typeof vi.fn>;
    stroke: ReturnType<typeof vi.fn>;
    globalCompositeOperation: string;
    fillStyle: string;
    strokeStyle: string;
    lineWidth: number;
    lineCap: CanvasLineCap;
    lineJoin: CanvasLineJoin;
};

describe('createBrushDrawer', () => {
    it('draws brush dots on the source context', () => {
        const context: Mock2dContext = {
            beginPath: vi.fn(),
            arc: vi.fn(),
            fill: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            stroke: vi.fn(),
            globalCompositeOperation: 'destination-over',
            fillStyle: 'transparent',
            strokeStyle: 'transparent',
            lineWidth: 0,
            lineCap: 'butt',
            lineJoin: 'bevel'
        };

        const ensureSourceMaskContext = vi.fn(() => context as unknown as CanvasRenderingContext2D);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushDot({
            point: { x: 3, y: 5 },
            brushRadius: 4,
            width: 100,
            height: 50
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledWith(100, 50);
        expect(context.beginPath).toHaveBeenCalledTimes(1);
        expect(context.arc).toHaveBeenCalledWith(3, 5, 4, 0, Math.PI * 2);
        expect(context.fill).toHaveBeenCalledTimes(1);
        expect(context.globalCompositeOperation).toBe('source-over');
        expect(context.fillStyle).toBe('black');
    });

    it('draws brush lines on the source context', () => {
        const context: Mock2dContext = {
            beginPath: vi.fn(),
            arc: vi.fn(),
            fill: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            stroke: vi.fn(),
            globalCompositeOperation: 'destination-over',
            fillStyle: 'transparent',
            strokeStyle: 'transparent',
            lineWidth: 0,
            lineCap: 'butt',
            lineJoin: 'bevel'
        };

        const ensureSourceMaskContext = vi.fn(() => context as unknown as CanvasRenderingContext2D);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushLine({
            from: { x: 1, y: 2 },
            to: { x: 10, y: 12 },
            brushRadius: 6,
            width: 100,
            height: 50
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledWith(100, 50);
        expect(context.beginPath).toHaveBeenCalledTimes(1);
        expect(context.moveTo).toHaveBeenCalledWith(1, 2);
        expect(context.lineTo).toHaveBeenCalledWith(10, 12);
        expect(context.stroke).toHaveBeenCalledTimes(1);
        expect(context.globalCompositeOperation).toBe('source-over');
        expect(context.strokeStyle).toBe('black');
        expect(context.lineWidth).toBe(12);
        expect(context.lineCap).toBe('round');
        expect(context.lineJoin).toBe('round');
    });

    it('does nothing when source context is unavailable', () => {
        const ensureSourceMaskContext = vi.fn(() => null);
        const brushDrawer = createBrushDrawer({ ensureSourceMaskContext });

        brushDrawer.drawBrushDot({
            point: { x: 0, y: 0 },
            brushRadius: 2,
            width: 10,
            height: 10
        });

        brushDrawer.drawBrushLine({
            from: { x: 0, y: 0 },
            to: { x: 1, y: 1 },
            brushRadius: 2,
            width: 10,
            height: 10
        });

        expect(ensureSourceMaskContext).toHaveBeenCalledTimes(2);
    });
});
