import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ConfusionMatrix from './ConfusionMatrix.svelte';
import { empty, small3Classes } from './fixtures';
import { OTHER_LABEL } from './topNMatrix';
import { NO_GROUND_TRUTH_ROW_LABEL } from './types';

const echartsMock = vi.hoisted(() => {
    let clickHandler: ((params: { value?: unknown }) => void) | undefined;
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn((event: string, handler: (params: { value?: unknown }) => void) => {
            if (event === 'click') clickHandler = handler;
        })
    };
    return {
        init: vi.fn(() => instance),
        getClickHandler: () => clickHandler
    };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ HeatmapChart: {} }));
vi.mock('echarts/components', () => ({
    TooltipComponent: {},
    VisualMapComponent: {},
    GridComponent: {},
    DataZoomInsideComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

describe('ConfusionMatrix', () => {
    it('renders the empty state when there are no labels', () => {
        render(ConfusionMatrix, { props: { matrix: empty } });
        expect(screen.getByTestId('confusion-matrix-empty')).toBeInTheDocument();
    });

    it('renders the chart container for a non-empty matrix', () => {
        render(ConfusionMatrix, { props: { matrix: small3Classes } });
        expect(screen.getByTestId('confusion-matrix')).toBeInTheDocument();
    });

    it('resolves a class-by-class cell click to (gt_label, pred_label)', () => {
        const onCellClick = vi.fn();
        render(ConfusionMatrix, { props: { matrix: small3Classes, onCellClick } });

        const handler = echartsMock.getClickHandler();
        expect(handler).toBeDefined();
        // Cell values are [pred, gt, count, log10(count)].
        handler?.({ value: ['dog', 'cat', 3, Math.log10(3)] });

        expect(onCellClick).toHaveBeenCalledWith({ gtLabel: 'cat', predLabel: 'dog' });
    });

    it('ignores clicks on the synthetic FP/FN cells', () => {
        const onCellClick = vi.fn();
        render(ConfusionMatrix, { props: { matrix: small3Classes, onCellClick } });

        const handler = echartsMock.getClickHandler();
        handler?.({ value: ['dog', NO_GROUND_TRUTH_ROW_LABEL, 1, 0] });

        expect(onCellClick).not.toHaveBeenCalled();
    });

    it('ignores clicks on the "(other)" aggregate cells', () => {
        const onCellClick = vi.fn();
        render(ConfusionMatrix, { props: { matrix: small3Classes, onCellClick } });

        const handler = echartsMock.getClickHandler();
        handler?.({ value: [OTHER_LABEL, 'cat', 1, 0] });
        handler?.({ value: ['dog', OTHER_LABEL, 1, 0] });

        expect(onCellClick).not.toHaveBeenCalled();
    });
});
