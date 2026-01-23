<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { PageData } from './$types';
    import { useTags } from '$lib/hooks/useTags/useTags';

    import { page } from '$app/state';

    const { data }: { data: PageData } = $props();
    const { sampleSize, selectedAnnotationFilterIds } = $derived(data);
    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);

    const { lastGridType } = useGlobalStorage();

    // Use root collection ID for tags - tags should always use root collection, not child collections
    const tagsCollectionId = $derived(datasetId ?? collectionId);

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
    {selectedAnnotationFilterIds}
/>
