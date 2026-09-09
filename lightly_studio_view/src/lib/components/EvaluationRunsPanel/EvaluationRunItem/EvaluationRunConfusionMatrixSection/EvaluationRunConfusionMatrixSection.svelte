<script lang="ts">
    import { page } from '$app/state';
    import type { ComponentProps } from 'svelte';
    import { Spinner, Typography } from '$lib/components';
    import {
        ConfusionMatrixPanel,
        NO_GROUND_TRUTH_ROW_LABEL,
        NO_PREDICTION_COL_LABEL,
        type ConfusionCellSelection
    } from '$lib/components/ConfusionMatrix';
    import { useEvaluationConfusionMatrix, usePostHog } from '$lib/hooks';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    interface Props {
        datasetId: string;
        evaluationRunId: string;
    }

    const { datasetId, evaluationRunId }: Props = $props();

    const collectionId = $derived(page.params.collection_id!);

    const { trackEvent } = usePostHog();

    const query = useEvaluationConfusionMatrix(() => ({
        datasetId,
        evaluationRunId
    }));

    const { updateConfusionCell } = useImageFilters();

    // Clicking a cell filters the image grid to the samples behind that bucket. The
    // chart emits camelCase labels; the API confusion-cell filter uses snake_case and
    // needs the owning run id. Synthetic axis labels map to null so the backend
    // resolves the false-positive (no ground truth) and false-negative (no prediction)
    // margin buckets.
    const handleCellClick = (cell: ConfusionCellSelection) => {
        const matrix = query.data;
        const rowIdx = matrix?.row_labels.indexOf(cell.gtLabel) ?? -1;
        const colIdx = matrix?.col_labels.indexOf(cell.predLabel) ?? -1;
        const sampleCount =
            rowIdx >= 0 && colIdx >= 0 ? (matrix?.counts[rowIdx]?.[colIdx] ?? 0) : 0;

        trackEvent('confusion_matrix_cell_clicked', {
            collection_id: collectionId,
            evaluation_run_id: evaluationRunId,
            actual_label: cell.gtLabel,
            predicted_label: cell.predLabel,
            sample_count: sampleCount
        });

        updateConfusionCell({
            evaluation_run_id: evaluationRunId,
            gt_label: cell.gtLabel === NO_GROUND_TRUTH_ROW_LABEL ? null : cell.gtLabel,
            pred_label: cell.predLabel === NO_PREDICTION_COL_LABEL ? null : cell.predLabel
        });
    };

    type MatrixExpandData = Parameters<
        NonNullable<ComponentProps<typeof ConfusionMatrixPanel>['onExpand']>
    >[0];

    const handleMatrixExpand = (data: MatrixExpandData) => {
        trackEvent('confusion_matrix_expanded', {
            collection_id: collectionId,
            evaluation_run_id: evaluationRunId,
            visible_class_count: data.visibleClassCount,
            total_class_count: data.totalClassCount
        });
    };

    type MatrixConfigApplied = Parameters<
        NonNullable<ComponentProps<typeof ConfusionMatrixPanel>['onConfigApplied']>
    >[0];

    const handleMatrixConfigApplied = (data: MatrixConfigApplied) => {
        trackEvent('confusion_matrix_configured', {
            collection_id: collectionId,
            evaluation_run_id: evaluationRunId,
            mode: data.mode,
            n: data.mode === 'topN' ? data.n : null,
            sort_by: data.sortBy,
            visible_class_count: data.visibleClassCount
        });
    };
</script>

{#if query.isLoading || query.isError || query.data}
    <section data-testid="evaluation-run-confusion-matrix">
        <Typography variant="subtitle2" component="h3" className="mb-3">Confusion Matrix</Typography
        >

        {#if query.isLoading}
            <div
                class="flex items-center justify-center py-8"
                data-testid="confusion-matrix-loading"
            >
                <Spinner size="medium" align="center" />
            </div>
        {:else if query.isError}
            <div class="py-4 text-center" data-testid="confusion-matrix-error">
                <Typography variant="body2" className="text-red-500">
                    {query.error?.message ?? 'Failed to load confusion matrix.'}
                </Typography>
            </div>
        {:else if query.data}
            <ConfusionMatrixPanel
                matrix={query.data}
                showLegend
                onCellClick={handleCellClick}
                onExpand={handleMatrixExpand}
                onConfigApplied={handleMatrixConfigApplied}
            />
        {/if}
    </section>
{/if}
