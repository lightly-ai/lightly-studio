<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { Spinner, Typography } from '$lib/components';
    import {
        ConfusionMatrixPanel,
        NO_GROUND_TRUTH_ROW_LABEL,
        NO_PREDICTION_COL_LABEL,
        type ConfusionCellSelection
    } from '$lib/components/ConfusionMatrix';
    import { useEvaluationConfusionMatrix } from '$lib/hooks';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { isEvaluationMatchesRoute } from '$lib/routes';
    import { MATCH_FILTER_NAV, setConfusionCellInUrl } from '$lib/utils';
    import type { ConfusionCell } from '$lib/api/lightly_studio_local';

    interface Props {
        evaluationRunId: string;
    }

    const { evaluationRunId }: Props = $props();

    const datasetId = $derived(page.params.dataset_id!);

    const query = useEvaluationConfusionMatrix(() => ({
        datasetId,
        evaluationRunId
    }));

    const { updateConfusionCell } = useImageFilters();

    // Clicking a cell filters to the samples/matches behind that bucket. The chart
    // emits camelCase labels; the API confusion-cell filter uses snake_case and needs
    // the owning run id. Synthetic axis labels map to null so the backend resolves the
    // false-positive (no ground truth) and false-negative (no prediction) margin
    // buckets. On the matches view the cell drives the matches grid via the URL
    // (replacing the history entry, not stacking one); everywhere else it drives the
    // image grid. Only the matrix of the run currently on screen may drive the URL, so
    // expanding another run's matrix in the panel cannot silently refilter the grid.
    const handleCellClick = (cell: ConfusionCellSelection) => {
        const confusionCell: ConfusionCell = {
            evaluation_run_id: evaluationRunId,
            gt_label: cell.gtLabel === NO_GROUND_TRUTH_ROW_LABEL ? null : cell.gtLabel,
            pred_label: cell.predLabel === NO_PREDICTION_COL_LABEL ? null : cell.predLabel
        };
        if (isEvaluationMatchesRoute(page.route.id)) {
            if (evaluationRunId === page.params.evaluation_run_id) {
                goto(setConfusionCellInUrl(page.url, confusionCell), MATCH_FILTER_NAV);
            }
        } else {
            updateConfusionCell(confusionCell);
        }
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
            <ConfusionMatrixPanel matrix={query.data} showLegend onCellClick={handleCellClick} />
        {/if}
    </section>
{/if}
