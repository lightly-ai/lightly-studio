import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EvaluationRunConfusionMatrixSection from './EvaluationRunConfusionMatrixSection.svelte';
import { coco80Classes, small3Classes } from '$lib/components/ConfusionMatrix/fixtures';

const queryState = vi.hoisted(() => ({
    isLoading: false,
    isError: false,
    data: undefined as unknown,
    error: undefined as Error | undefined
}));

const filtersMock = vi.hoisted(() => ({
    updateConfusionCell: vi.fn()
}));

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

vi.mock('$app/state', () => ({
    page: { params: { dataset_id: 'ds-1' } }
}));

vi.mock('$lib/hooks', () => ({
    useEvaluationConfusionMatrix: vi.fn(() => queryState)
}));

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: vi.fn(() => filtersMock)
}));

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

const defaultProps = { evaluationRunId: 'run-1' };

describe('EvaluationRunConfusionMatrixSection', () => {
    beforeEach(() => {
        filtersMock.updateConfusionCell.mockClear();
    });

    it('shows a spinner while loading', () => {
        queryState.isLoading = true;
        queryState.isError = false;
        queryState.data = undefined;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        expect(screen.getByTestId('confusion-matrix-loading')).toBeInTheDocument();
        expect(screen.queryByTestId('confusion-matrix-error')).not.toBeInTheDocument();
    });

    it('shows the error message when the query fails', () => {
        queryState.isLoading = false;
        queryState.isError = true;
        queryState.data = undefined;
        queryState.error = new Error('boom');

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const errorEl = screen.getByTestId('confusion-matrix-error');
        expect(errorEl).toHaveTextContent('boom');
    });

    it('falls back to a generic error message when no error message is provided', () => {
        queryState.isLoading = false;
        queryState.isError = true;
        queryState.data = undefined;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        expect(screen.getByTestId('confusion-matrix-error')).toHaveTextContent(
            'Failed to load confusion matrix.'
        );
    });

    it('hides the section when data is null and not loading', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = null;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        expect(screen.queryByTestId('evaluation-run-confusion-matrix')).not.toBeInTheDocument();
    });

    it('renders the panel with controls for a small matrix', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        expect(screen.queryByTestId('confusion-matrix-loading')).not.toBeInTheDocument();
        expect(screen.queryByTestId('confusion-matrix-error')).not.toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix')).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix-configure')).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix-expand')).toBeInTheDocument();
    });

    it('renders the panel with controls for a large matrix', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = coco80Classes;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        expect(screen.getByTestId('confusion-matrix-configure')).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix-expand')).toBeInTheDocument();
    });

    it('applies a confusion-cell filter (with the run id) when a cell is clicked', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const handler = echartsMock.getClickHandler();
        expect(handler).toBeDefined();
        // Cell values are [pred, gt, count, log10(count)].
        handler?.({ value: ['dog', 'cat', 3, Math.log10(3)] });

        expect(filtersMock.updateConfusionCell).toHaveBeenCalledWith({
            evaluation_run_id: 'run-1',
            gt_label: 'cat',
            pred_label: 'dog'
        });
    });
});
