<script lang="ts">
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
    import { Typography } from '$lib/components';
    import { formatDate } from '$lib/utils';
    import { TriangleAlert } from '@lucide/svelte';
    import EvaluationRunSummary from './EvaluationRunSummary/EvaluationRunSummary.svelte';
    import EvaluationRunConfiguration from './EvaluationRunConfiguration/EvaluationRunConfiguration.svelte';
    import { slide } from 'svelte/transition';
    import EvaluationRunConfusionMatrixSection from './EvaluationRunConfusionMatrixSection/EvaluationRunConfusionMatrixSection.svelte';
    import EvaluationRunStaleSection from './EvaluationRunStaleSection/EvaluationRunStaleSection.svelte';
    import EditEvaluationDialog from '../EditEvaluationDialog/EditEvaluationDialog.svelte';
    import DeleteEvaluationRun from '../DeleteEvaluationRun/DeleteEvaluationRun.svelte';

    let editing = $state(false);
    const duration = 300; // in ms

    interface Props {
        /** The dataset the evaluation run belongs to. Required to enable the recompute action. */
        datasetId?: string;
        /** The evaluation run to display. */
        run: EvaluationRunView;
        /** Whether the details section is expanded. */
        expanded: boolean;
        /** Callback to toggle the expanded state. */
        onToggle: () => void;
    }

    const { datasetId, run, expanded, onToggle }: Props = $props();
</script>

<li class="relative rounded-md border border-border bg-background">
    <button
        type="button"
        class="block w-full px-3 py-2 text-left hover:bg-muted/50"
        onclick={onToggle}
        data-testid={`evaluation-run-item-${run.name}`}
        aria-expanded={expanded}
    >
        <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 pr-8">
                <Typography
                    variant={expanded ? 'subtitle1' : 'subtitle2'}
                    className="truncate"
                    props={{ 'data-testid': 'evaluation-run-name' }}
                >
                    {run.name}
                </Typography>
                {#if run.stale_since !== null}
                    <TriangleAlert
                        class="{expanded
                            ? 'size-4'
                            : 'size-3.5'} shrink-0 text-amber-500 dark:text-amber-400"
                        data-testid="evaluation-run-stale-icon"
                    />
                {/if}
            </div>
            <Typography
                variant="caption"
                className="text-muted-foreground"
                props={{ 'data-testid': 'evaluation-run-date' }}
            >
                {formatDate(run.created_at)}
            </Typography>
            <EvaluationRunSummary
                groundTruth={run.gt_annotation_source}
                predictions={run.pred_annotation_source}
            />
        </div>
    </button>
    {#if datasetId}
        <div class="absolute right-1 top-1 text-muted-foreground">
            <DeleteEvaluationRun {datasetId} run={{ id: run.id, name: run.name }} />
        </div>
    {/if}

    {#if expanded}
        <div
            class="space-y-5 border-t border-border px-3 py-3"
            data-testid="evaluation-run-details"
            transition:slide={{ duration }}
        >
            {#if run.stale_since !== null && datasetId}
                <EvaluationRunStaleSection />
            {/if}

            <EvaluationRunConfiguration
                configuration={run.evaluation_run_configuration}
                onEdit={datasetId ? () => (editing = true) : undefined}
            />

            <EvaluationRunConfusionMatrixSection
                datasetId={datasetId ?? ''}
                evaluationRunId={run.id}
            />
        </div>
    {/if}
</li>

{#if editing && datasetId}
    <EditEvaluationDialog {datasetId} {run} onClose={() => (editing = false)} />
{/if}
