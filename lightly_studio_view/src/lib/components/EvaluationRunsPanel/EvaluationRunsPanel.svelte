<script lang="ts">
    import { X } from '@lucide/svelte';
    import Button from '$lib/components/ui/button/button.svelte';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import Typography from '$lib/components/Typography/Typography.svelte';

    import EvaluationRunItem from './EvaluationRunItem/EvaluationRunItem.svelte';
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
    }

    const { onClose, evaluationRuns, isLoading = false, error }: Props = $props();

    let expandedRunId = $state<string | null>(null);
    const toggleExpand = (runId: string) => {
        expandedRunId = expandedRunId === runId ? null : runId;
    };
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
            onclick={onClose}
            aria-label="Close evaluation runs panel"
            class="h-8 w-8"
            data-testid="evaluation-runs-close-button"
        >
            <X class="size-4" />
        </Button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {#if isLoading}
            <div class="flex flex-1 items-center justify-center p-8">
                <Spinner size="medium" align="center" />
            </div>
        {:else if error}
            <div class="flex flex-1 items-center justify-center p-8">
                <Typography variant="body2" className="text-red-500">
                    Error loading evaluation runs:
                    {error ?? 'Unknown error'}
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
