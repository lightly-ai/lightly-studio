<script lang="ts">
    import { page } from '$app/state';
    import { Spinner, Typography } from '$lib/components';
    import {
        ConfusionMatrixPanel,
        type ConfusionCellSelection
    } from '$lib/components/ConfusionMatrix';
    import { useEvaluationConfusionMatrix } from '$lib/hooks';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

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

    // Clicking a real class-by-class cell filters the image grid to the samples
    // behind that confusion bucket. The chart emits camelCase labels; the API
    // confusion-cell filter uses snake_case and needs the owning run id.
    const handleCellClick = (cell: ConfusionCellSelection) => {
        updateConfusionCell({
            evaluation_run_id: evaluationRunId,
            gt_label: cell.gtLabel,
            pred_label: cell.predLabel
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
            <ConfusionMatrixPanel matrix={query.data} showLegend onCellClick={handleCellClick} />
        {/if}
    </section>
{/if}
