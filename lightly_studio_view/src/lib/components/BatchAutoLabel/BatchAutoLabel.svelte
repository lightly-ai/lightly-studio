<script lang="ts">
    import { get } from 'svelte/store';
    import { useAnnotationCollections, useGlobalStorage } from '$lib/hooks';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import AutoLabelDialog from './AutoLabelDialog/AutoLabelDialog.svelte';
    import AutoLabelDock from './AutoLabelDock/AutoLabelDock.svelte';
    import { useBatchAutoLabel } from './useBatchAutoLabel.svelte';

    interface Props {
        collectionId: string;
        datasetId: string;
        selectedCount: number;
        isDialogOpen: boolean;
    }

    let { collectionId, datasetId, selectedCount, isDialogOpen = $bindable() }: Props = $props();

    const { getSelectedSampleIds } = useGlobalStorage();
    const { setSelectedCollectionIds } = useAnnotationCollectionsFilter();
    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const batch = useBatchAutoLabel({
        getCollectionId: () => collectionId,
        getDatasetId: () => datasetId
    });
    const batchState = batch.state;

    const start = (params: { modelId: string; threshold: number; classNames: string[] }) => {
        const sampleIds = [...get(getSelectedSampleIds(collectionId))];
        void batch.start({ ...params, sampleIds });
    };

    // Shows only the annotations of the run's source.
    const viewResults = async () => {
        const { data: sources } = await annotationCollectionsQuery.refetch();
        const source = sources?.find(({ name }) => name === $batchState.modelId);
        if (source) setSelectedCollectionIds([source.collection_id]);
        batch.reset();
    };
</script>

<AutoLabelDialog bind:open={isDialogOpen} {selectedCount} onStart={start} />
{#if $batchState.status !== 'idle' && $batchState.modelId}
    <AutoLabelDock
        status={$batchState.status}
        modelId={$batchState.modelId}
        total={$batchState.total}
        done={$batchState.done}
        annotationCount={$batchState.annotationCount}
        failedCount={$batchState.failedCount}
        onStop={batch.stop}
        onViewResults={() => void viewResults()}
        onClose={batch.reset}
    />
{/if}
