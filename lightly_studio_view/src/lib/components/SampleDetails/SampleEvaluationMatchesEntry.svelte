<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { EvaluationTaskType } from '$lib/api/lightly_studio_local';
    import { Typography } from '$lib/components';
    import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { routeHelpers } from '$lib/routes';
    import { LayoutGrid } from '@lucide/svelte';

    type Props = {
        sampleId: string;
        datasetId: string;
    };

    const { sampleId, datasetId }: Props = $props();

    const runsQuery = useEvaluationRuns(() => ({ datasetId }));

    // Per-box matches only exist for object detection runs.
    const objectDetectionRuns = $derived(
        (runsQuery.data ?? []).filter(
            (run) => run.task_type === EvaluationTaskType.OBJECT_DETECTION
        )
    );

    // Runs come back newest first, so the first one is the most recent.
    let selectedRunId = $state<string | null>(null);
    const effectiveRunId = $derived(selectedRunId ?? objectDetectionRuns[0]?.id ?? null);

    // Default the selector to the most recent run once runs have loaded.
    $effect(() => {
        if (selectedRunId === null && objectDetectionRuns.length > 0) {
            selectedRunId = objectDetectionRuns[0].id;
        }
    });

    const viewMatches = () => {
        if (!effectiveRunId) return;
        goto(
            routeHelpers.toEvaluationMatches({
                datasetId: page.params.dataset_id!,
                collectionType: page.params.collection_type!,
                collectionId: page.params.collection_id!,
                evaluationRunId: effectiveRunId,
                sampleIds: [sampleId]
            })
        );
    };
</script>

{#if objectDetectionRuns.length > 0}
    <div
        class="space-y-2 rounded-md border border-border bg-background p-3"
        data-testid="sample-evaluation-matches-entry"
    >
        <Typography variant="subtitle2">Evaluation matches</Typography>
        <Typography variant="caption" className="text-muted-foreground">
            Inspect the TP/FP/FN boxes for this image.
        </Typography>
        <select
            class="w-full rounded-md border border-border bg-muted px-2 py-1.5 text-sm"
            bind:value={selectedRunId}
            data-testid="sample-evaluation-matches-run-select"
        >
            {#each objectDetectionRuns as run (run.id)}
                <option value={run.id}>{run.name}</option>
            {/each}
        </select>
        <button
            type="button"
            class="flex w-full items-center justify-center gap-2 rounded-md border border-border bg-muted px-3 py-2 text-sm font-medium hover:bg-muted/70"
            onclick={viewMatches}
            data-testid="sample-evaluation-matches-view"
        >
            <LayoutGrid class="size-4" />
            View matches for this image
        </button>
    </div>
{/if}
