<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { SideMenu } from '$lib/components/SideMenu';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import {
        useAnnotationCollectionsFilter,
        DEFAULT_COLLECTION_COLORS
    } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const annotationCollectionsQuery = useAnnotationCollections({ collectionId });
    const items = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    const {
        setSelectedCollectionIds,
        setCollectionIdToName,
        selectedCollectionIds,
        collectionIdToColor,
        setCollectionIdToColor,
        setCollectionColor
    } = useAnnotationCollectionsFilter();

    let initialized = $state(false);

    const isEnabled = $derived(items.length > 1);

    $effect(() => {
        if (isEnabled && !initialized) {
            initialized = true;
            setSelectedCollectionIds(items.map((i) => i.id));
            setCollectionIdToName(
                Object.fromEntries(items.map((i: { id: string; name: string }) => [i.id, i.name]))
            );
            setCollectionIdToColor(
                Object.fromEntries(
                    items.map((i, idx) => [
                        i.id,
                        DEFAULT_COLLECTION_COLORS[idx % DEFAULT_COLLECTION_COLORS.length]
                    ])
                )
            );
        }
    });

    const itemsWithColors = $derived(
        items.map((item) => ({ ...item, color: $collectionIdToColor[item.id] }))
    );
</script>

{#if isEnabled}
    <Segment title="Annotation Sources">
        <SideMenu
            showColorMarker={$selectedCollectionIds.length > 1}
            items={itemsWithColors}
            initialSelectedItemsIds={items.map((i) => i.id)}
            onChangeSelectedItems={setSelectedCollectionIds}
            onColorChange={(id, color) => setCollectionColor(id, color)}
        />
    </Segment>
{/if}
