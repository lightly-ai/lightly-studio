<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { SideMenu } from '$lib/components/SideMenu';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const annotationCollectionsQuery = useAnnotationCollections({ collectionId });
    const items = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    const { setSelectedCollectionIds, setCollectionIdToName, selectedCollectionIds } =
        useAnnotationCollectionsFilter();

    let initialized = $state(false);

    const isEnabled = $derived(items.length > 1);

    $effect(() => {
        if (isEnabled && !initialized) {
            initialized = true;
            setSelectedCollectionIds(items.map((i) => i.id));
            setCollectionIdToName(
                Object.fromEntries(items.map((i: { id: string; name: string }) => [i.id, i.name]))
            );
        }
    });
</script>

{#if isEnabled}
    <Segment title="Annotation Sources">
        <SideMenu
            showColorMarker={$selectedCollectionIds.length > 1}
            enableColorPicker
            {items}
            initialSelectedItemsIds={items.map((i) => i.id)}
            onChangeSelectedItems={setSelectedCollectionIds}
        />
    </Segment>
{/if}
