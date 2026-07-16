import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Histogram from './Histogram.svelte';
import { empty, normal, singleBin } from './fixtures';

const defaultProps = { data: normal };

const echartsMock = vi.hoisted(() => {
    const zrHandlers: Record<string, (event: { offsetX: number; offsetY: number }) => void> = {};
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn(),
        // 20 bins across a 200px-wide canvas → 10px per bin index.
        convertFromPixel: vi.fn((_finder: unknown, offsetX: number) => offsetX / 10),
        getZr: () => ({
            on: (event: string, handler: (event: { offsetX: number; offsetY: number }) => void) => {
                zrHandlers[event] = handler;
            },
            off: vi.fn()
        })
    };
    return { init: vi.fn(() => instance), instance, zrHandlers };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ CustomChart: {} }));
vi.mock('echarts/components', () => ({
    GridComponent: {},
    TooltipComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

describe('Histogram', () => {
    it('renders the chart container for a distribution with bins', () => {
        render(Histogram, { props: defaultProps });
        expect(screen.getByTestId('histogram')).toBeInTheDocument();
    });

    it('renders a single-bin distribution', () => {
        render(Histogram, { props: { ...defaultProps, data: singleBin } });
        expect(screen.getByTestId('histogram')).toBeInTheDocument();
    });

    it('renders nothing when there are no counts', () => {
        render(Histogram, { props: { ...defaultProps, data: empty } });
        expect(screen.queryByTestId('histogram')).not.toBeInTheDocument();
    });

    it('renders nothing when there are fewer than two bin edges', () => {
        render(Histogram, {
            props: { ...defaultProps, data: { binEdges: [1], counts: [5] } }
        });
        expect(screen.queryByTestId('histogram')).not.toBeInTheDocument();
    });

    it('applies the requested height to the container', () => {
        render(Histogram, { props: { ...defaultProps, heightPx: 240 } });
        expect(screen.getByTestId('histogram')).toHaveStyle({ height: '240px' });
    });

    it('defaults to the inline sparkline height', () => {
        render(Histogram, { props: defaultProps });
        expect(screen.getByTestId('histogram')).toHaveStyle({ height: '48px' });
    });

    it('pushes the built option to the chart instance', () => {
        render(Histogram, { props: defaultProps });
        expect(echartsMock.init).toHaveBeenCalled();
        expect(echartsMock.instance.setOption).toHaveBeenCalled();
    });

    it('resolves a single click to that bin interval', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        // Press and release over bin 2 (offsetX 25 → index 2.5 → bin 2).
        echartsMock.zrHandlers.mousedown({ offsetX: 25, offsetY: 10 });
        window.dispatchEvent(new MouseEvent('mouseup'));

        // normal: 20 bins over [0, 100] → bin 2 covers [10, 15).
        expect(onRangeSelect).toHaveBeenCalledWith({ min: 10, max: 15 });
    });

    it('resolves press-drag-release to the spanned range', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        echartsMock.zrHandlers.mousedown({ offsetX: 25, offsetY: 10 }); // bin 2
        echartsMock.zrHandlers.mousemove({ offsetX: 68, offsetY: 10 }); // bin 6
        window.dispatchEvent(new MouseEvent('mouseup'));

        // Bins 2..6 span [10, 35).
        expect(onRangeSelect).toHaveBeenCalledWith({ min: 10, max: 35 });
        expect(onRangeSelect).toHaveBeenCalledOnce();
    });

    it('supports dragging right-to-left', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        echartsMock.zrHandlers.mousedown({ offsetX: 68, offsetY: 10 }); // bin 6
        echartsMock.zrHandlers.mousemove({ offsetX: 25, offsetY: 10 }); // bin 2
        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onRangeSelect).toHaveBeenCalledWith({ min: 10, max: 35 });
    });

    it('clamps drags past the chart edges to the domain', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        echartsMock.zrHandlers.mousedown({ offsetX: 150, offsetY: 10 }); // bin 15
        echartsMock.zrHandlers.mousemove({ offsetX: 9999, offsetY: 10 }); // past the right edge
        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onRangeSelect).toHaveBeenCalledWith({ min: 75, max: 100 });
    });

    it('tracks drags that move outside the canvas', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        echartsMock.zrHandlers.mousedown({ offsetX: 150, offsetY: 10 }); // bin 15
        window.dispatchEvent(new MouseEvent('mousemove', { clientX: 9999 }));
        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onRangeSelect).toHaveBeenCalledWith({ min: 75, max: 100 });
    });

    it('does nothing on mouseup without a preceding press', () => {
        const onRangeSelect = vi.fn();
        render(Histogram, { props: { ...defaultProps, onRangeSelect } });

        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onRangeSelect).not.toHaveBeenCalled();
    });

    it('ignores presses when no onRangeSelect handler is provided', () => {
        render(Histogram, { props: defaultProps });

        echartsMock.zrHandlers.mousedown({ offsetX: 25, offsetY: 10 });
        expect(() => window.dispatchEvent(new MouseEvent('mouseup'))).not.toThrow();
    });
});
