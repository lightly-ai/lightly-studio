import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ConfusionMatrix from './ConfusionMatrix.svelte';
import { empty, small3Classes } from './fixtures';

vi.mock('echarts/core', () => ({
    init: vi.fn(() => ({
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn()
    })),
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
});
