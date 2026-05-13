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
        ($annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    const { setSelectedCollectionIds, setCollectionIdToName } = useAnnotationCollectionsFilter();

    let initialized = $state(false);

    $effect(() => {
        if (items.length > 0 && !initialized) {
            initialized = true;
            setSelectedCollectionIds(items.map((i) => i.id));
            setCollectionIdToName(Object.fromEntries(items.map((i: { id: string; name: string }) => [i.id, i.name])));
        }
    });
</script>

{#if items.length > 0}
    <Segment title="Collections">
        <SideMenu
            showColorMarker={true}
            {items}
            initialSelectedItemsIds={items.map((i) => i.id)}
            onChangeSelectedItems={setSelectedCollectionIds}
        />
    </Segment>
{/if}
