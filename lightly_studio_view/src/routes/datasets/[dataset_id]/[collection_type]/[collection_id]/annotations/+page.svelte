<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useTags } from '$lib/hooks/useTags/useTags';

    import { page } from '$app/state';

    const collectionId = $derived(page.params.collection_id!);

    const { lastGridType, sampleSize } = useGlobalStorage();

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

<AnnotationsGrid itemWidth={$sampleSize.width} collection_id={collectionId} />
