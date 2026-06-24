<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import { Label } from '$lib/components/ui/label';
    import Select from '$lib/components/Select/Select.svelte';
    import { Spinner } from '$lib/components';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import ObjectDetectionConfigFields from './ObjectDetectionConfigFields.svelte';
    import { useTriggerEvaluation } from './useTriggerEvaluation.svelte';
    import {
        buildEvaluationRunBody,
        canSubmitEvaluation,
        sourceMatchesTask,
        type EvaluationTaskType
    } from './TriggerEvaluationDialog.helpers';

    type TaskType = EvaluationTaskType;

    interface Props {
        /** Dataset the run belongs to. */
        datasetId: string;
        /** Collection (active view) the run evaluates on. */
        collectionId: string;
        /** Whether the dialog is open. */
        open: boolean;
        /** Called when the dialog open state changes. */
        onOpenChange: (open: boolean) => void;
    }

    const { datasetId, collectionId, open, onOpenChange }: Props = $props();

    const taskTypeItems: { value: TaskType; label: string }[] = [
        { value: 'object_detection', label: 'Object Detection' },
        { value: 'classification', label: 'Classification' },
        { value: 'semantic_segmentation', label: 'Semantic Segmentation' }
    ];

    let taskType = $state<TaskType>('object_detection');
    let gtSource = $state<string | undefined>(undefined);
    let predSource = $state<string | undefined>(undefined);
    let iouThreshold = $state(0.5);
    let classwise = $state(true);

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const sources = $derived(annotationCollectionsQuery.data ?? []);

    // Only sources whose annotations match the selected task type are valid
    // (mirrors the backend validator), so the user can't pick an incompatible one.
    const matchingSources = $derived(
        sources.filter((source) => sourceMatchesTask(source.annotation_types ?? [], taskType))
    );
    const hasNoMatchingSources = $derived(matchingSources.length === 0);

    const sourceItems = (excluded: string | undefined) =>
        matchingSources.map((source) => ({
            value: source.name,
            label: source.name,
            disabled: source.name === excluded
        }));

    const onTaskTypeChange = (value: string) => {
        taskType = value as TaskType;
        // Sources valid for the previous task may not be valid now.
        gtSource = undefined;
        predSource = undefined;
    };

    const { mutation, trigger } = useTriggerEvaluation(() => ({ datasetId }));
    const isSubmitting = $derived(mutation.isPending);

    const sameSource = $derived(!!gtSource && gtSource === predSource);
    const canSubmit = $derived(canSubmitEvaluation({ gtSource, predSource, isSubmitting }));

    const handleSubmit = async (event: SubmitEvent) => {
        event.preventDefault();
        if (!canSubmit) return;
        const ok = await trigger(
            buildEvaluationRunBody({
                taskType,
                gtSource: gtSource!,
                predSource: predSource!,
                collectionId,
                iouThreshold,
                classwise
            })
        );
        if (ok) {
            gtSource = undefined;
            predSource = undefined;
            onOpenChange(false);
        }
    };
</script>

<Dialog.Root {open} {onOpenChange}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[480px]">
            <form onsubmit={handleSubmit} data-testid="trigger-evaluation-form">
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Start evaluation</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Evaluate predictions against ground truth on this dataset.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    <div class="grid gap-2">
                        <Label class="text-foreground">Evaluation type</Label>
                        <Select
                            items={taskTypeItems}
                            value={taskType}
                            onValueChange={onTaskTypeChange}
                            testId="evaluation-type-select"
                        />
                    </div>

                    {#if hasNoMatchingSources}
                        <p
                            class="text-sm text-muted-foreground"
                            data-testid="no-matching-sources-warning"
                        >
                            No annotation sources with matching annotations were found for this
                            evaluation type.
                        </p>
                    {:else}
                        <div class="grid gap-2">
                            <Label class="text-foreground">Ground truth source</Label>
                            <Select
                                items={sourceItems(predSource)}
                                value={gtSource}
                                placeholder="Select a source"
                                onValueChange={(value) => (gtSource = value)}
                                testId="gt-source-select"
                            />
                        </div>

                        <div class="grid gap-2">
                            <Label class="text-foreground">Prediction source</Label>
                            <Select
                                items={sourceItems(gtSource)}
                                value={predSource}
                                placeholder="Select a source"
                                onValueChange={(value) => (predSource = value)}
                                testId="pred-source-select"
                            />
                        </div>
                    {/if}

                    {#if sameSource}
                        <p class="text-sm text-destructive-text" data-testid="same-source-warning">
                            Ground truth and prediction sources must be different.
                        </p>
                    {/if}

                    {#if taskType === 'object_detection'}
                        <ObjectDetectionConfigFields bind:iouThreshold bind:classwise />
                    {/if}

                    <p class="text-xs text-muted-foreground" data-testid="evaluation-duration-note">
                        Evaluation runs on the full dataset and may take a while to complete.
                    </p>
                </div>

                <Dialog.Footer>
                    <Button
                        variant="outline"
                        type="button"
                        onclick={() => onOpenChange(false)}
                        disabled={isSubmitting}
                        data-testid="trigger-evaluation-cancel"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!canSubmit}
                        data-testid="trigger-evaluation-submit"
                    >
                        {#if isSubmitting}
                            <Spinner size="small" />
                            Evaluating…
                        {:else}
                            Start evaluation
                        {/if}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
