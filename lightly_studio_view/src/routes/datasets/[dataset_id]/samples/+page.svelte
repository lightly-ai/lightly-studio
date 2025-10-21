<script lang="ts">
    import { Samples } from '$lib/components/index.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { useTags } from '$lib/hooks/useTags/useTags';

    const { data } = $props();
    const {
        datasetId: dataset_id,
        sampleSize,
        selectedAnnotationFilterIds,
        globalStorage: { textEmbedding }
    } = data;

    const { lastGridType } = useGlobalStorage();

    const { clearTagsSelected } = $derived(
        useTags({
            dataset_id
        })
    );

    $effect(() => {
        if ($lastGridType !== 'samples') {
            clearTagsSelected();
        }
    });
</script>

<Samples
    sampleHeight={$sampleSize.height}
    sampleWidth={$sampleSize.width}
    {textEmbedding}
    {dataset_id}
    {selectedAnnotationFilterIds}
/>
