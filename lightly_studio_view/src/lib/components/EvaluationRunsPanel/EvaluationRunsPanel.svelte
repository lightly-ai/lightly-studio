<script lang="ts">
    import { page } from '$app/state';
    import Button from '$lib/components/ui/button/button.svelte';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import EvaluationRunItem from './EvaluationRunItem/EvaluationRunItem.svelte';

    const datasetId = $derived(page.data.collection.dataset_id);
    const { setShowEvaluationRuns } = useGlobalStorage();

    const evaluationRunsQuery = $derived(useEvaluationRuns({ datasetId }));
    const evaluationRuns = $derived($evaluationRunsQuery.data ?? []);

    let expandedRunId = $state<string | null>(null);
    const toggleExpand = (runId: string) => {
        expandedRunId = expandedRunId === runId ? null : runId;
    };

    const handleClose = () => setShowEvaluationRuns(false);
</script>

<div
    class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4"
    data-testid="evaluation-runs-panel"
>
    <div class="mb-5 mt-2 flex items-center justify-between">
        <Typography variant="h5" component="h2" className="text-foreground">
            Evaluation Runs
        </Typography>
        <Button
            variant="ghost"
            size="icon"
            onclick={handleClose}
            class="h-8 w-8"
            data-testid="evaluation-runs-close-button"
        >
            ✕
        </Button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {#if $evaluationRunsQuery.isLoading}
            <div class="flex flex-1 items-center justify-center p-8">
                <Spinner size="medium" align="center" />
            </div>
        {:else if $evaluationRunsQuery.isError}
            <div class="flex flex-1 items-center justify-center p-8">
                <Typography variant="body2" className="text-red-500">
                    Error loading evaluation runs:
                    {$evaluationRunsQuery.error?.message ?? 'Unknown error'}
                </Typography>
            </div>
        {:else if evaluationRuns.length === 0}
            <div
                class="flex flex-1 items-center justify-center p-8"
                data-testid="evaluation-runs-empty"
            >
                <div class="text-center">
                    <Typography variant="body1">No evaluation runs yet</Typography>
                    <Typography variant="body2" className="mt-1 text-muted-foreground">
                        Runs will appear here once you compute them for this dataset.
                    </Typography>
                </div>
            </div>
        {:else}
            <ul class="flex flex-col gap-2" data-testid="evaluation-runs-list">
                {#each evaluationRuns as run (run.id)}
                    <EvaluationRunItem
                        {run}
                        expanded={expandedRunId === run.id}
                        onToggle={() => toggleExpand(run.id)}
                    />
                {/each}
            </ul>
        {/if}
    </div>
</div>
