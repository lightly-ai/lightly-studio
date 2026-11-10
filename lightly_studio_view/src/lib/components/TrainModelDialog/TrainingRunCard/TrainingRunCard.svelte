<script lang="ts">
    import { Button } from '$lib/components';
    import type { TrainingRunView } from '$lib/api/lightly_studio_local/types.gen';
    import { STATUS_LABELS, progressPercent } from '../TrainModelDialog.helpers';

    interface Props {
        run: TrainingRunView;
        isCancelling: boolean;
        onCancel: () => void;
    }

    let { run, isCancelling, onCancel }: Props = $props();

    const percent = $derived(progressPercent(run));
    const canCancel = $derived(run.status === 'training' || run.status === 'predicting');
</script>

<div class="grid gap-2 rounded-md border border-border p-3" data-testid="training-run-card">
    <div class="flex items-center justify-between gap-2">
        <span class="truncate text-sm font-medium text-foreground">{run.name}</span>
        <span class="text-sm text-muted-foreground" data-testid="training-run-status">
            {STATUS_LABELS[run.status]}
        </span>
    </div>
    <p class="text-xs text-muted-foreground">
        {run.model_name} · {run.train_sample_count} train · {run.val_sample_count} val images
    </p>
    {#if run.status === 'training'}
        <div class="h-2 w-full overflow-hidden rounded bg-muted">
            <div class="h-full bg-primary transition-all" style="width: {percent ?? 0}%"></div>
        </div>
        <p class="text-xs text-muted-foreground" data-testid="training-run-progress">
            {#if run.current_step}
                Step {run.current_step} of {run.total_steps}{run.train_loss != null
                    ? ` · loss ${run.train_loss.toFixed(3)}`
                    : ''}
            {:else}
                Preparing the model…
            {/if}
        </p>
    {/if}
    {#if run.status === 'completed'}
        <p class="text-xs text-muted-foreground">
            The predictions are in the annotation source "{run.name}". The evaluation run has the
            same name.
        </p>
    {/if}
    {#if run.error}
        <pre
            class="max-h-32 overflow-auto whitespace-pre-wrap text-xs text-destructive-text"
            data-testid="training-run-error">{run.error}</pre>
    {/if}
    {#if canCancel}
        <Button
            variant="outline"
            isPending={isCancelling}
            buttonProps={{
                type: 'button',
                onclick: onCancel,
                disabled: isCancelling,
                'data-testid': 'training-run-cancel'
            }}
        >
            Cancel training
        </Button>
    {/if}
</div>
