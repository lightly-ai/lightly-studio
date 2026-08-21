<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { SideMenu } from '$lib/components/SideMenu';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks';
    import { resolveEffectiveColorBySource } from '$lib/utils';
    import { get } from 'svelte/store';
    import { handleAnnotationSourceFilterChange } from './handleAnnotationSourceFilterChange';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const items = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    const { setSelectedCollectionIds, selectedCollectionIds, multipleSourcesVisible } =
        useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { trackEvent } = usePostHog();

    // Checkboxes are only worth showing when there is a choice to make. The selection itself is
    // filled by useSeedAnnotationSourceFilter in the collection layout, which runs for every
    // collection including those with a single source.
    const isEnabled = $derived(items.length > 1);

    const handleChangeSelectedItems = (newIds: string[]) => {
        handleAnnotationSourceFilterChange({
            newIds,
            prevIds: get(selectedCollectionIds),
            items,
            collectionId,
            setSelectedCollectionIds,
            trackEvent
        });
    };
</script>

{#if isEnabled}
    <Segment title="Annotation Sources">
        <SideMenu
            showColorMarker={resolveEffectiveColorBySource({
                multipleSourcesVisible: $multipleSourcesVisible,
                enforceColoringByClass: $enforceColoringByClassStore
            })}
            enableColorPicker
            {items}
            selectedItemsIds={$selectedCollectionIds}
            onChangeSelectedItems={handleChangeSelectedItems}
        />
    </Segment>
{/if}
