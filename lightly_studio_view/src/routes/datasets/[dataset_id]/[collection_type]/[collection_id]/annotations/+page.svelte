<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { PageData } from './$types';
    import { useTags } from '$lib/hooks/useTags/useTags';

    const { data }: { data: PageData } = $props();
    const { sampleSize, selectedAnnotationFilterIds, datasetId, collection } = data;
    const collectionId = collection?.collection_id ?? '';

    const { lastGridType } = useGlobalStorage();

    // Use root collection ID for tags - tags should always use root collection, not child collections
    const tagsCollectionId = datasetId ?? collectionId;

    const { clearTagsSelected } = $derived(
        useTags({
            collection_id: tagsCollectionId
        })
    );

    $effect(() => {
        if ($lastGridType !== 'annotations') {
            clearTagsSelected();
        }
    });
</script>

<AnnotationsGrid
    itemWidth={$sampleSize.width}
    collection_id={collectionId}
    {datasetId}
    {selectedAnnotationFilterIds}
/>
