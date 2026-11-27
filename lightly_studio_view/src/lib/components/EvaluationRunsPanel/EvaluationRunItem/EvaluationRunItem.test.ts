import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import { get } from 'svelte/store';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import { formatDate } from '$lib/utils';
import EvaluationRunItem from './EvaluationRunItem.svelte';
import EvaluationRunConfiguration from './EvaluationRunConfiguration/EvaluationRunConfiguration.svelte';

vi.mock(
    './EvaluationRunConfusionMatrixSection/EvaluationRunConfusionMatrixSection.svelte',
    async () => {
        const module =
            await import('./EvaluationRunConfusionMatrixSection/EvaluationRunConfusionMatrixSection.mock.svelte');
        return { default: module.default };
    }
);

const deletion = vi.hoisted(() => ({ isPending: false, mutate: vi.fn() }));
let callbacks: { onSuccess: () => void; onError: () => void };
vi.mock('@tanstack/svelte-query', async (original) => ({
    ...(await original<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
    createMutation: (options: () => typeof callbacks) => {
        callbacks = options();
        return deletion;
    }
}));
const state = vi.hoisted(() => ({ pending: false, params: vi.fn(), recompute: vi.fn() }));
beforeEach(() => {
    vi.clearAllMocks();
    state.pending = false;
});
vi.mock('$lib/hooks/useRecomputeEvaluationRun/useRecomputeEvaluationRun.svelte', () => ({
    useRecomputeEvaluationRun: (getParams: () => unknown) => {
        state.params.mockImplementation(getParams);
        return {
            mutation: { isPending: state.pending },
            recompute: state.recompute
        };
    }
}));

const baseRun: EvaluationRunView = {
    id: 'run-1',
    name: 'Detection eval — v1',
    evaluation_run_configuration: {
        iou_threshold: 0.75,
        split: 'val',
        classwise: true
    },
    created_at: new Date('2026-01-15T10:30:00Z'),
    stale_since: null,
    gt_annotation_source: 'ground_truth_v1',
    pred_annotation_source: 'predictions_v2'
};

const defaultProps = {
    datasetId: 'dataset-1',
    run: baseRun,
    expanded: false,
    onToggle: vi.fn()
};
const baseRunItemTestId = `evaluation-run-item-${baseRun.name}`;

describe('EvaluationRunItem', () => {
    it('does not offer editing when configuration is missing', () => {
        render(EvaluationRunConfiguration, { configuration: null, onEdit: vi.fn() });
        expect(screen.getByText('No configuration recorded.')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    });

    it('renders the run name and creation date', () => {
        render(EvaluationRunItem, { props: { ...defaultProps } });

        expect(screen.getByTestId('evaluation-run-name')).toHaveTextContent('Detection eval — v1');
        expect(screen.getByTestId('evaluation-run-date')).toHaveTextContent(
            formatDate(baseRun.created_at)
        );
        expect(screen.getByTestId(baseRunItemTestId)).toHaveAttribute('aria-expanded', 'false');
    });

    it('hides configuration details when collapsed', () => {
        render(EvaluationRunItem, { props: { ...defaultProps } });

        expect(screen.queryByTestId('evaluation-run-details')).not.toBeInTheDocument();
        const summary = screen.getByTestId(baseRunItemTestId);
        expect(summary).toHaveTextContent('Predictions predictions_v2');
        expect(summary).toHaveTextContent('Ground truth ground_truth_v1');
        expect(summary).not.toHaveTextContent('Minimum overlap');
        expect(summary).not.toHaveTextContent('Class matching');
    });

    it('renders configuration entries and opens editing for a current run', async () => {
        render(EvaluationRunItem, { props: { ...defaultProps, expanded: true } });

        const details = screen.getByTestId('evaluation-run-details');
        expect(details).toBeInTheDocument();
        expect(details).toHaveTextContent('Minimum overlap (IoU)');
        expect(details).toHaveTextContent('0.75');
        expect(details).toHaveTextContent('split');
        expect(details).toHaveTextContent('val');
        expect(details).toHaveTextContent('Class matching');
        expect(details).toHaveTextContent('Same class only');
        expect(screen.getByTestId(baseRunItemTestId)).toHaveAttribute('aria-expanded', 'true');
        await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
        expect(screen.getByRole('dialog')).toHaveTextContent(baseRun.name);
        await fireEvent.click(screen.getByRole('switch'));
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(state.recompute).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
        expect(screen.getByRole('switch')).toBeChecked();
    });

    it.each([
        [true, 'Computed'],
        [false, 'Not computed']
    ])('renders the average precision setting %s as %s', (computeAveragePrecision, text) => {
        const run: EvaluationRunView = {
            ...baseRun,
            evaluation_run_configuration: {
                ...baseRun.evaluation_run_configuration,
                compute_average_precision: computeAveragePrecision
            }
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        const details = screen.getByTestId('evaluation-run-details');
        expect(details).toHaveTextContent('Average precision');
        expect(details).toHaveTextContent(text);
    });

    it('shows a placeholder and allows rerunning without adjustable parameters', async () => {
        const run: EvaluationRunView = { ...baseRun, evaluation_run_configuration: {} };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        expect(screen.queryByTestId('evaluation-run-config')).not.toBeInTheDocument();
        expect(screen.getByTestId('evaluation-run-details')).toHaveTextContent(
            'No configuration recorded.'
        );
        await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
        expect(screen.queryByRole('slider')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Save and rerun' }));
        expect(state.params().config).toEqual({});
    });

    it('serializes nested config values as JSON', () => {
        const run: EvaluationRunView = {
            ...baseRun,
            evaluation_run_configuration: { classes: ['cat', 'dog'] }
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        expect(screen.getByTestId('evaluation-run-config')).toHaveTextContent('["cat","dog"]');
    });

    it('shows unknown sources when their names are unavailable', () => {
        const run = { ...baseRun, gt_annotation_source: null, pred_annotation_source: null };
        render(EvaluationRunItem, { props: { ...defaultProps, run } });

        expect(screen.getByTestId('evaluation-run-gt-annotation-source')).toHaveTextContent(
            'Unknown'
        );
        expect(screen.getByTestId('evaluation-run-prediction-annotation-source')).toHaveTextContent(
            'Unknown'
        );
    });

    it('formats class-agnostic matching and missing configuration values', () => {
        const run = {
            ...baseRun,
            evaluation_run_configuration: { classwise: false, split: null }
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        expect(screen.getByTestId('evaluation-run-config')).toHaveTextContent('Any class');
        expect(screen.getByTestId('evaluation-run-config')).toHaveTextContent('—');
    });

    it('calls onToggle when the row is clicked', async () => {
        const onToggle = vi.fn();
        render(EvaluationRunItem, { props: { ...defaultProps, onToggle } });

        await fireEvent.click(screen.getByTestId(baseRunItemTestId));
        expect(onToggle).toHaveBeenCalledOnce();
    });

    it('renders the GT and prediction annotation sources when expanded', () => {
        render(EvaluationRunItem, { props: { ...defaultProps, expanded: true } });

        expect(screen.getByTestId('evaluation-run-annotation-sources')).toBeInTheDocument();
        expect(screen.getByTestId('evaluation-run-gt-annotation-source')).toHaveTextContent(
            'ground_truth_v1'
        );
        expect(screen.getByTestId('evaluation-run-prediction-annotation-source')).toHaveTextContent(
            'predictions_v2'
        );
    });

    it('shows the stale icon when stale_since is set', () => {
        const run: EvaluationRunView = {
            ...baseRun,
            stale_since: new Date('2026-02-01T00:00:00Z')
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run } });

        expect(screen.getByTestId('evaluation-run-stale-icon')).toBeInTheDocument();
    });

    it('shows stale guidance and offers editing when stale and expanded', () => {
        const run: EvaluationRunView = {
            ...baseRun,
            stale_since: new Date('2026-02-01T00:00:00Z')
        };
        render(EvaluationRunItem, { props: { ...defaultProps, run, expanded: true } });

        const staleSection = screen.getByTestId('evaluation-run-stale-section');
        expect(staleSection).toHaveTextContent(
            'Annotations changed. Edit the settings and rerun to update these results.'
        );
        expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    });

    it('does not show the recompute button when datasetId is not provided', () => {
        const run: EvaluationRunView = {
            ...baseRun,
            stale_since: new Date('2026-02-01T00:00:00Z')
        };
        render(EvaluationRunItem, {
            props: { ...defaultProps, datasetId: undefined, run, expanded: true }
        });

        expect(screen.queryByTestId('evaluation-run-stale-section')).not.toBeInTheDocument();
    });
    it('loads saved values, submits changes to the same run, and closes only after success', async () => {
        render(EvaluationRunItem, { ...defaultProps, expanded: true });
        await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
        await fireEvent.click(screen.getByRole('switch'));
        await fireEvent.click(screen.getByRole('button', { name: 'Save and rerun' }));
        expect(state.recompute).toHaveBeenCalledOnce();
        expect(state.params()).toMatchObject({
            datasetId: 'dataset-1',
            runId: baseRun.id,
            config: { iou_threshold: 0.75, classwise: false, split: 'val' }
        });
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        state.params().onSuccess();
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });

    it('blocks cancellation and repeated submissions while rerunning', async () => {
        state.pending = true;
        render(EvaluationRunItem, { ...defaultProps, expanded: true });
        await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
        expect(screen.getByRole('button', { name: 'Evaluating…' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
        await fireEvent.keyDown(document, { key: 'Escape' });
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
});

it.each(['run-1', 'other-run'])(
    'confirms deletion and clears only its selections (%s)',
    async (selectedRun) => {
        const filters = useImageFilters();
        const annotations = useAnnotationSortBy();
        const sort = [
            {
                source: 'evaluation_metric' as const,
                evaluation_run_name: selectedRun,
                metric_name: 'fp',
                direction: 'desc' as const
            }
        ];
        const cell = { evaluation_run_id: selectedRun, gt_label: 'cat', pred_label: 'dog' };
        const annotationSort = {
            source: 'annotation_evaluation_metric' as const,
            evaluation_run_id: selectedRun,
            metric_name: 'iou',
            direction: 'asc' as const
        };
        filters.updateFilterParams({
            collection_id: 'images',
            mode: 'normal',
            filters: { tag_ids: ['tag'], confusion_cell: cell }
        });
        filters.updateSortBy(sort);
        annotations.setSortBy('source', annotationSort);
        render(EvaluationRunItem, { ...defaultProps, run: { ...baseRun, name: 'run-1' } });
        const open = () =>
            fireEvent.click(screen.getByRole('button', { name: 'Delete evaluation run-1' }));
        await open();
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(deletion.mutate).not.toHaveBeenCalled();
        await open();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        expect(deletion.mutate).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', run_id: 'run-1' }
        });
        callbacks.onError();
        expect(get(filters.imageSortBy)).toEqual(sort);
        expect(get(filters.imageFilter)?.sample_filter?.confusion_cell).toEqual(cell);
        expect(annotations.getSortBy('source')).toEqual(annotationSort);
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        callbacks.onSuccess();
        expect(get(filters.imageSortBy)).toEqual(selectedRun === 'run-1' ? null : sort);
        expect(get(filters.imageFilter)?.sample_filter).toEqual({
            tag_ids: ['tag'],
            confusion_cell: selectedRun === 'run-1' ? undefined : cell
        });
        expect(annotations.getSortBy('source')).toEqual(
            selectedRun === 'run-1' ? null : annotationSort
        );
        expect(defaultProps.onToggle).not.toHaveBeenCalled();
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    }
);
