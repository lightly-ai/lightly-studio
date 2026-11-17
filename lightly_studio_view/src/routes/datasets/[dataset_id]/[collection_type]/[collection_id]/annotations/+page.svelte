<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { getFlatAnnotationTreeCollectionId } from '$lib/components/AnnotationTree';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useTags } from '$lib/hooks/useTags/useTags';

    import { page } from '$app/state';

    const collectionId = $derived(page.params.collection_id!);

    const { lastGridType, sampleSize } = useGlobalStorage();
    const treeCollectionId = getFlatAnnotationTreeCollectionId();

    const { clearTagsSelected } = $derived(
        useTags({
            collection_id: collectionId
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
    treeCollectionId={treeCollectionId()}
/>
