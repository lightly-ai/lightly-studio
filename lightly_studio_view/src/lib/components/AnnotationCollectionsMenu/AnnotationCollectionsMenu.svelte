<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { FilterList } from '$lib/components/FilterList';
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks';
    import { resolveEffectiveColorBySource } from '$lib/utils';
    import { get } from 'svelte/store';
    import { handleAnnotationSourceFilterChange } from './handleAnnotationSourceFilterChange';
    import DeleteAnnotationSource from './DeleteAnnotationSource/DeleteAnnotationSource.svelte';

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

    // A single source is listed too, so that it can be deleted. The selection itself is filled by
    // useSeedAnnotationSourceFilter in the collection layout, which runs for every collection.
    const isEnabled = $derived(items.length > 0);

    const showColorMarker = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );
    const filterItems = $derived(
        items.map(({ id, name }) => ({
            id,
            label: name,
            selected: $selectedCollectionIds.includes(id)
        }))
    );
    const toggleItem = (id: string) => {
        const selected = get(selectedCollectionIds);
        handleChangeSelectedItems(
            selected.includes(id) ? selected.filter((other) => other !== id) : [...selected, id]
        );
    };

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
        <FilterList
            items={filterItems}
            onToggle={toggleItem}
            onSelectionChange={handleChangeSelectedItems}
            testId="annotation-sources-menu"
            searchPlaceholder="Search annotation sources…"
        >
            {#snippet leading(item)}
                {#if showColorMarker}
                    <ColorMarker
                        label={item.label}
                        enableColorPicker
                        markerProps={{ 'data-testid': `color-marker-${item.label}` }}
                    />
                {/if}
            {/snippet}
            {#snippet trailing(item)}
                <DeleteAnnotationSource {collectionId} source={{ id: item.id, name: item.label }} />
            {/snippet}
        </FilterList>
    </Segment>
{/if}
