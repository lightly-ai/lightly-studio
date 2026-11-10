<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { sourceMatchesTask } from '$lib/components/EvaluationRunsPanel/TriggerEvaluationDialog/TriggerEvaluationDialog.helpers';
    import { useTrainModelDialog } from '$lib/hooks/useTrainModelDialog/useTrainModelDialog';
    import TrainModelForm from './TrainModelForm/TrainModelForm.svelte';
    import TrainingRunCard from './TrainingRunCard/TrainingRunCard.svelte';
    import { useTrainingRuns } from './useTrainingRuns.svelte';
    import { isActiveRun } from './TrainModelDialog.helpers';

    interface Props {
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const { isTrainModelDialogOpen, closeTrainModelDialog } = useTrainModelDialog();
    const { tags } = $derived(useTags({ collection_id: collectionId }));
    const sourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const { query, startMutation, cancelMutation, start, cancel } = useTrainingRuns(() => ({
        collectionId
    }));

    const tagOptions = $derived($tags.map((tag) => ({ value: tag.tag_id, label: tag.name })));
    const sourceOptions = $derived(
        (sourcesQuery.data ?? [])
            .filter((source) =>
                sourceMatchesTask(source.annotation_types ?? [], 'object_detection')
            )
            .map((source) => ({ value: source.collection_id, label: source.name }))
    );
    const latestRun = $derived(query.data?.[0]);
</script>

<Dialog.Root
    open={$isTrainModelDialogOpen}
    onOpenChange={(open) => !open && closeTrainModelDialog()}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[480px]">
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Train a model</Dialog.Title>
                <Dialog.Description class="text-foreground">
                    Train an object detection model with LightlyTrain. Its predictions for all
                    images go into a new annotation source, and are evaluated on the val tag.
                </Dialog.Description>
            </Dialog.Header>
            <div class="grid gap-4 py-2">
                {#if latestRun}
                    <TrainingRunCard
                        run={latestRun}
                        isCancelling={cancelMutation.isPending}
                        onCancel={() => cancel(latestRun.training_run_id)}
                    />
                {/if}
                {#if !isActiveRun(latestRun)}
                    <TrainModelForm
                        {tagOptions}
                        {sourceOptions}
                        isStarting={startMutation.isPending}
                        onStart={start}
                    />
                {/if}
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
