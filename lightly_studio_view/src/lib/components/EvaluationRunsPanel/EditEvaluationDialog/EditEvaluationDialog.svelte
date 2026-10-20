<script lang="ts">
    import { untrack } from 'svelte';
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useRecomputeEvaluationRun } from '$lib/hooks';
    import ObjectDetectionConfigFields from '../TriggerEvaluationDialog/ObjectDetectionConfigFields.svelte';
    import EvaluationRunSummary from '../EvaluationRunItem/EvaluationRunSummary/EvaluationRunSummary.svelte';

    interface Props {
        datasetId: string;
        run: EvaluationRunView;
        onClose: () => void;
    }
    const { datasetId, run, onClose }: Props = $props();
    // This dialog mounts for each edit, so cancelled changes never become saved defaults.
    const config = untrack(() => run.evaluation_run_configuration);
    const hasMatchingSettings = typeof config.iou_threshold === 'number';
    let iouThreshold = $state(
        typeof config.iou_threshold === 'number' ? config.iou_threshold : 0.5
    );
    let classwise = $state(config.classwise === true);
    const { mutation, recompute } = useRecomputeEvaluationRun(() => ({
        datasetId,
        runId: run.id,
        onSuccess: onClose,
        config: hasMatchingSettings ? { ...config, iou_threshold: iouThreshold, classwise } : config
    }));
    const close = () => {
        if (!mutation.isPending) onClose();
    };
    const submit = (event: SubmitEvent) => {
        event.preventDefault();
        if (mutation.isPending) return;
        recompute();
    };
</script>

<Dialog.Root bind:open={() => true, close}>
    <Dialog.Content>
        <form onsubmit={submit}>
            <Dialog.Header>
                <Dialog.Title>Edit and rerun</Dialog.Title>
                <Dialog.Description>
                    Update results using all samples covered by the saved annotation sources.
                </Dialog.Description>
            </Dialog.Header>
            <div class="grid gap-4 py-4">
                <p class="break-words text-sm font-medium">{run.name}</p>
                <EvaluationRunSummary
                    groundTruth={run.gt_annotation_source}
                    predictions={run.pred_annotation_source}
                />
                <fieldset disabled={mutation.isPending} class="grid gap-4">
                    {#if hasMatchingSettings}
                        <ObjectDetectionConfigFields bind:iouThreshold bind:classwise />
                    {:else}
                        <p class="text-sm text-muted-foreground">
                            This evaluation has no adjustable parameters.
                        </p>
                    {/if}
                </fieldset>
            </div>
            <Dialog.Footer>
                <Button
                    variant="outline"
                    buttonProps={{ type: 'button', disabled: mutation.isPending, onclick: close }}
                    >Cancel</Button
                >
                <Button
                    isPending={mutation.isPending}
                    buttonProps={{ type: 'submit', disabled: mutation.isPending }}
                >
                    {mutation.isPending ? 'Evaluating…' : 'Save and rerun'}
                </Button>
            </Dialog.Footer>
        </form>
    </Dialog.Content>
</Dialog.Root>
