<script lang="ts">
    import { ArrowLeft, Plus, X } from '@lucide/svelte';
    import Button from '$lib/components/ui/button/button.svelte';
    import { Spinner, Typography } from '$lib/components';

    import EvaluationRunItem from './EvaluationRunItem/EvaluationRunItem.svelte';
    import TriggerEvaluationDialog from './TriggerEvaluationDialog/TriggerEvaluationDialog.svelte';
    import { type EvaluationRunView } from '$lib/api/lightly_studio_local';

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
        /** Runs to render. When empty and not loading/errored, the empty state is shown. */
        evaluationRuns: EvaluationRunView[];
        /** Shows a spinner instead of the list. Takes precedence over `error` and `evaluationRuns`. */
        isLoading?: boolean;
        /** Error message to display in place of the list. Ignored while `isLoading` is true. */
        error?: string;
        /** Dataset the runs belong to. When set with `collectionId`, enables the trigger dialog. */
        datasetId?: string;
        /** Collection (active view) to evaluate on. Required to enable the trigger dialog. */
        collectionId?: string;
    }

    const {
        onClose,
        evaluationRuns,
        isLoading = false,
        error,
        datasetId,
        collectionId
    }: Props = $props();

    const canTrigger = $derived(!!datasetId && !!collectionId);
    let dialogOpen = $state(false);

    let expandedRunId = $state<string | null>(null);
    const expandedRun = $derived(
        expandedRunId ? (evaluationRuns.find((run) => run.id === expandedRunId) ?? null) : null
    );
    const visibleRuns = $derived(expandedRun ? [expandedRun] : evaluationRuns);
    const toggleExpand = (runId: string) => {
        expandedRunId = expandedRunId === runId ? null : runId;
    };
    const collapseExpanded = () => {
        expandedRunId = null;
    };
</script>

<div
    class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4"
    data-testid="evaluation-runs-panel"
>
    <div class="mb-5 mt-2 flex items-center justify-between">
        <div class="flex min-w-0 items-center gap-1">
            {#if expandedRun}
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={collapseExpanded}
                    aria-label="Back to all evaluation runs"
                    class="h-8 w-8"
                    data-testid="evaluation-runs-back-button"
                >
                    <ArrowLeft class="size-4" />
                </Button>
            {/if}
            <Typography variant="h5" component="h2" className="text-foreground">
                Evaluation Runs
            </Typography>
        </div>
        <div class="flex items-center gap-1">
            {#if canTrigger}
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={() => (dialogOpen = true)}
                    aria-label="Start a new evaluation run"
                    class="h-8 w-8"
                    data-testid="evaluation-runs-add-button"
                >
                    <Plus class="size-4" />
                </Button>
            {/if}
            <Button
                variant="ghost"
                size="icon"
                onclick={onClose}
                aria-label="Close evaluation runs panel"
                class="h-8 w-8"
                data-testid="evaluation-runs-close-button"
            >
                <X class="size-4" />
            </Button>
        </div>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto dark:[color-scheme:dark]">
        {#if isLoading}
            <div class="flex flex-1 items-center justify-center p-8">
                <Spinner size="medium" align="center" />
            </div>
        {:else if error}
            <div class="flex flex-1 items-center justify-center p-8">
                <Typography variant="body2" className="text-red-500">
                    Error loading evaluation runs:
                    {error}
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
                {#each visibleRuns as run (run.id)}
                    <EvaluationRunItem
                        {run}
                        expanded={expandedRunId === run.id}
                        onToggle={() => toggleExpand(run.id)}
                    />
                {/each}
            </ul>
        {/if}
    </div>

    {#if canTrigger}
        <TriggerEvaluationDialog
            datasetId={datasetId!}
            collectionId={collectionId!}
            open={dialogOpen}
            onOpenChange={(open) => (dialogOpen = open)}
        />
    {/if}
</div>
