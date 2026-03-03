<script lang="ts">
    import { Samples } from '$lib/components/index.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { page } from '$app/state';
    import { toStore } from 'svelte/store';

    const { data } = $props();

    const {
        sampleSize,
        selectedAnnotationFilterIds,
        globalStorage: { textEmbedding }
    } = data;

    const collection_id = $derived(page.params.collection_id!);
    const collectionIdStore = toStore(() => collection_id);

    const { lastGridType } = useGlobalStorage();

    const { clearTagsSelected } = useTags({
        collection_id: collectionIdStore
    });

    $effect(() => {
        if ($lastGridType !== 'samples') {
            clearTagsSelected();
        }
    });
</script>

<Samples
    sampleWidth={$sampleSize.width}
    {textEmbedding}
    {collection_id}
    {selectedAnnotationFilterIds}
/>
