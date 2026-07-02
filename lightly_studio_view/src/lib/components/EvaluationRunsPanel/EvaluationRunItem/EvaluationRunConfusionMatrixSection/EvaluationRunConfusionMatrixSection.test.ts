import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EvaluationRunConfusionMatrixSection from './EvaluationRunConfusionMatrixSection.svelte';
import { coco80Classes, small3Classes } from '$lib/components/ConfusionMatrix/fixtures';
import { APP_ROUTES } from '$lib/routes';

const queryState = vi.hoisted(() => ({
    isLoading: false,
    isError: false,
    data: undefined as unknown,
    error: undefined as Error | undefined
}));

// Mutable so individual tests can switch the active route between the images view
// (where a cell click drives the image filter) and the matches view (where it
// drives the matches grid via a URL change). Default to a non-matches route.
const pageMock = vi.hoisted(() => ({
    params: { dataset_id: 'ds-1', evaluation_run_id: 'run-1' } as Record<string, string>,
    route: { id: '/datasets/[dataset_id]/[collection_type]/[collection_id]' } as {
        id: string | null;
    },
    url: new URL('http://localhost/datasets/ds-1/annotation/col/evaluation/run-1/matches')
}));

const gotoMock = vi.hoisted(() => vi.fn());

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
    page: pageMock
}));

vi.mock('$app/navigation', () => ({
    goto: gotoMock
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
        gotoMock.mockClear();
        pageMock.route.id = '/datasets/[dataset_id]/[collection_type]/[collection_id]';
        pageMock.params = { dataset_id: 'ds-1', evaluation_run_id: 'run-1' };
        pageMock.url = new URL(
            'http://localhost/datasets/ds-1/annotation/col/evaluation/run-1/matches'
        );
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

    it('maps a false-positive cell (FP row) to a null gt_label', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const handler = echartsMock.getClickHandler();
        // [pred, gt, ...]: spurious "dog" prediction in the "(no ground truth)" row.
        handler?.({ value: ['dog', '(no ground truth)', 1, 0] });

        expect(filtersMock.updateConfusionCell).toHaveBeenCalledWith({
            evaluation_run_id: 'run-1',
            gt_label: null,
            pred_label: 'dog'
        });
    });

    it('maps a false-negative cell (FN column) to a null pred_label', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const handler = echartsMock.getClickHandler();
        // [pred, gt, ...]: missed "cat" ground truth in the "(no prediction)" column.
        handler?.({ value: ['(no prediction)', 'cat', 1, 0] });

        expect(filtersMock.updateConfusionCell).toHaveBeenCalledWith({
            evaluation_run_id: 'run-1',
            gt_label: 'cat',
            pred_label: null
        });
    });

    it('drives the matches confusion cell via a URL change (not the image filter) on the matches view', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;
        pageMock.route.id = APP_ROUTES.evaluationMatches;

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const handler = echartsMock.getClickHandler();
        handler?.({ value: ['dog', 'cat', 3, Math.log10(3)] });

        expect(filtersMock.updateConfusionCell).not.toHaveBeenCalled();
        expect(gotoMock).toHaveBeenCalledTimes(1);
        const [target, options] = gotoMock.mock.calls[0];
        const params = new URL(target, 'http://localhost').searchParams;
        expect(params.get('cc_gt')).toBe('cat');
        expect(params.get('cc_pred')).toBe('dog');
        expect(options).toMatchObject({ replaceState: true });
    });

    it('ignores a matrix cell click for a run other than the one on screen', () => {
        queryState.isLoading = false;
        queryState.isError = false;
        queryState.data = small3Classes;
        queryState.error = undefined;
        pageMock.route.id = APP_ROUTES.evaluationMatches;
        pageMock.params = { dataset_id: 'ds-1', evaluation_run_id: 'other-run' };

        render(EvaluationRunConfusionMatrixSection, { props: defaultProps });

        const handler = echartsMock.getClickHandler();
        handler?.({ value: ['dog', 'cat', 3, Math.log10(3)] });

        expect(gotoMock).not.toHaveBeenCalled();
        expect(filtersMock.updateConfusionCell).not.toHaveBeenCalled();
    });
});
