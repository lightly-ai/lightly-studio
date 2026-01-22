<script lang="ts">
    import { Samples } from '$lib/components/index.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { useTags } from '$lib/hooks/useTags/useTags';

    const { data } = $props();
    const {
        collection,
        sampleSize,
        selectedAnnotationFilterIds,
        globalStorage: { textEmbedding }
    } = data;

    const collection_id = $derived(collection?.collection_id ?? '');

    const { lastGridType } = useGlobalStorage();

    const { clearTagsSelected } = $derived(
        useTags({
            collection_id
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
    {collection_id}
    {selectedAnnotationFilterIds}
/>
