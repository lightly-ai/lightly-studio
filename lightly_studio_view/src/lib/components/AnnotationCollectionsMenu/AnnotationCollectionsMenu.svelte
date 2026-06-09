<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { SideMenu } from '$lib/components/SideMenu';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const items = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    const { setSelectedCollectionIds, selectedCollectionIds, seedSelectionIfNeeded } =
        useAnnotationCollectionsFilter();

    const isEnabled = $derived(items.length > 1);

    // Seed all sources the first time this collection is shown; remounts (e.g. returning
    // from image details) keep the user's existing selection. See seedSelectionIfNeeded.
    $effect(() => {
        if (isEnabled) {
            seedSelectionIfNeeded(collectionId, items);
        }
    });
</script>

{#if isEnabled}
    <Segment title="Annotation Sources">
        <SideMenu
            showColorMarker={$selectedCollectionIds.length > 1}
            enableColorPicker
            {items}
            selectedItemsIds={$selectedCollectionIds}
            onChangeSelectedItems={setSelectedCollectionIds}
        />
    </Segment>
{/if}
