<script lang="ts">
    import { page } from '$app/state';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useEvaluationRuns, useConfusionMatrix } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { Button } from '$lib/components/ui/button';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import ConfusionMatrix from '$lib/components/ConfusionMatrix/ConfusionMatrix.svelte';
    import { Settings2, ArrowLeft } from '@lucide/svelte';
    import type { EvaluationRunView } from '$lib/api/evaluationRunApi';

    const datasetId = $derived(page.params.dataset_id!);
    const { setShowEvalPanel, selectedEvaluationRunId, setSelectedEvaluationRunId } =
        useGlobalStorage();

    const runsQuery = $derived(useEvaluationRuns(datasetId));
    const runs = $derived($runsQuery.data ?? []);

    const selectedRun = $derived(runs.find((r) => r.id === $selectedEvaluationRunId) ?? null);

    const confusionMatrixQuery = $derived(useConfusionMatrix($selectedEvaluationRunId));
    const confusionMatrixData = $derived($confusionMatrixQuery.data ?? null);

    function handleClose() {
        setShowEvalPanel(false);
    }

    function selectRun(run: EvaluationRunView) {
        setSelectedEvaluationRunId(run.id);
    }

    function goBack() {
        setSelectedEvaluationRunId(null);
    }
</script>

<div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4" data-testid="eval-panel">
    {#if selectedRun}
        <!-- Detail view -->
        <div class="mb-4 mt-2 flex items-center justify-between">
            <div class="flex min-w-0 items-center gap-2">
                <Button variant="ghost" size="icon" onclick={goBack} class="h-8 w-8 shrink-0">
                    <ArrowLeft class="h-4 w-4" />
                </Button>
                <div class="min-w-0">
                    <div class="truncate text-lg font-semibold">{selectedRun.name}</div>
                    <div class="text-xs text-muted-foreground">{selectedRun.task_type}</div>
                </div>
            </div>
            <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8 shrink-0">✕</Button>
        </div>

        <div class="min-h-0 flex-1 space-y-2 overflow-y-auto">
            <Segment title="Config" icon={Settings2}>
                <div class="space-y-1 text-xs text-muted-foreground">
                    <div class="flex justify-between">
                        <span>GT</span>
                        <span class="max-w-36 truncate font-mono text-foreground" title={selectedRun.gt_collection_name}>
                            {selectedRun.gt_collection_name}
                        </span>
                    </div>
                    <div class="flex justify-between">
                        <span>Pred</span>
                        <span class="max-w-36 truncate font-mono text-foreground" title={selectedRun.pred_collection_name}>
                            {selectedRun.pred_collection_name}
                        </span>
                    </div>
                    {#each Object.entries(selectedRun.config_json) as [key, value]}
                        <div class="flex justify-between">
                            <span>{key}</span>
                            <span class="font-mono text-foreground">{String(value)}</span>
                        </div>
                    {/each}
                </div>
            </Segment>

            <Segment title="Confusion Matrix">
                {#if $confusionMatrixQuery.isLoading}
                    <div class="py-4 text-center text-xs text-muted-foreground">Loading…</div>
                {:else if confusionMatrixData && confusionMatrixData.cells.length > 0}
                    <ConfusionMatrix
                        cells={confusionMatrixData.cells}
                        labels={confusionMatrixData.labels}
                    />
                {:else}
                    <div class="py-4 text-center text-xs text-muted-foreground">No match data</div>
                {/if}
            </Segment>
        </div>
    {:else}
        <!-- List view -->
        <div class="mb-4 mt-2 flex items-center justify-between">
            <div class="text-lg font-semibold">Evaluation</div>
            <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8">✕</Button>
        </div>

        {#if $runsQuery.isLoading}
            <div class="flex items-center justify-center p-8 text-sm text-muted-foreground">
                Loading…
            </div>
        {:else if runs.length === 0}
            <div class="flex items-center justify-center p-8 text-sm text-muted-foreground">
                No evaluation runs
            </div>
        {:else}
            <div class="min-h-0 flex-1 overflow-y-auto">
                <div class="space-y-1">
                    {#each runs as run (run.id)}
                        <button
                            class="w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent"
                            onclick={() => selectRun(run)}
                        >
                            <div class="truncate font-medium">{run.name}</div>
                            <div class="text-xs text-muted-foreground">{run.task_type}</div>
                        </button>
                    {/each}
                </div>
            </div>
        {/if}
    {/if}
</div>
