<script lang="ts">
    import { page } from '$app/state';
    import { Spinner, Typography } from '$lib/components';
    import { ConfusionMatrix } from '$lib/components/ConfusionMatrix';
    import { useEvaluationConfusionMatrix } from '$lib/hooks';

    interface Props {
        evaluationRunId: string;
    }

    const { evaluationRunId }: Props = $props();

    const datasetId = $derived(page.params.dataset_id!);

    const query = useEvaluationConfusionMatrix(() => ({
        datasetId,
        evaluationRunId
    }));
</script>

<section data-testid="evaluation-run-confusion-matrix">
    <Typography variant="subtitle2" component="h3" className="mb-3">Confusion Matrix</Typography>

    {#if query.isLoading}
        <div class="flex items-center justify-center py-8" data-testid="confusion-matrix-loading">
            <Spinner size="medium" align="center" />
        </div>
    {:else if query.isError}
        <div class="py-4 text-center" data-testid="confusion-matrix-error">
            <Typography variant="body2" className="text-red-500">
                {query.error?.message ?? 'Failed to load confusion matrix.'}
            </Typography>
        </div>
    {:else if query.data}
        <ConfusionMatrix matrix={query.data} showLegend />
    {/if}
</section>
