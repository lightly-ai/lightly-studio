import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ConfusionMatrixPanel from './ConfusionMatrixPanel.svelte';
import { coco80Classes, small3Classes } from '../fixtures';

vi.mock('echarts/core', () => ({
    init: vi.fn(() => ({
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn()
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

describe('ConfusionMatrixPanel', () => {
    it('always shows the controls, even for a small matrix', () => {
        render(ConfusionMatrixPanel, { props: { matrix: small3Classes } });

        expect(screen.getByTestId('confusion-matrix')).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix-configure')).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix-expand')).toBeInTheDocument();
    });

    it('defaults to the top-N view regardless of matrix size', () => {
        render(ConfusionMatrixPanel, { props: { matrix: coco80Classes } });

        expect(screen.getByTestId('confusion-matrix-configure')).toBeInTheDocument();
        expect(screen.getByText(/Top 5 of 80 classes/)).toBeInTheDocument();
    });

    it('respects a custom topN value', () => {
        render(ConfusionMatrixPanel, { props: { matrix: coco80Classes, topN: 10 } });

        expect(screen.getByText(/Top 10 of 80 classes/)).toBeInTheDocument();
    });
});
