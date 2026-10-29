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
    import { ItemActionMenu } from '$lib/components/ItemActionMenu';
    import { ItemRenameInput } from '$lib/components/ItemRenameInput';
    import DeleteAnnotationSource from './DeleteAnnotationSource/DeleteAnnotationSource.svelte';
    import { useRenameAnnotationSource } from './useRenameAnnotationSource/useRenameAnnotationSource';

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

    let openActionsSourceId = $state<string | null>(null);
    let editingSourceId = $state<string | null>(null);
    let deletingSource = $state<{ id: string; name: string } | null>(null);
    const { rename, renamingId } = useRenameAnnotationSource(() => ({
        collectionId,
        sources: items,
        onRenamed: () => (editingSourceId = null)
    }));

    // A single source is listed too, so that it can be renamed or deleted. The selection itself is filled by
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
            customRowId={editingSourceId}
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
                {@const source = { id: item.id, name: item.label }}
                <ItemActionMenu
                    id={source.id}
                    name={source.name}
                    kind="annotation source"
                    open={openActionsSourceId === source.id}
                    deletingId={deletingSource?.id ?? null}
                    renamingId={$renamingId}
                    onOpenChange={(open) => (openActionsSourceId = open ? source.id : null)}
                    onCloseAutoFocus={(event) => {
                        // Keep the focus in the rename input.
                        if (editingSourceId === source.id) event.preventDefault();
                    }}
                    onRename={(event) => {
                        event.stopPropagation();
                        openActionsSourceId = null;
                        editingSourceId = source.id;
                    }}
                    onDelete={(event) => {
                        event.stopPropagation();
                        openActionsSourceId = null;
                        deletingSource = source;
                    }}
                />
            {/snippet}
            {#snippet customRow(item)}
                <ItemRenameInput
                    id={item.id}
                    name={item.label}
                    kind="annotation source"
                    renamingId={$renamingId}
                    checked={item.selected}
                    onCheckedChange={() => toggleItem(item.id)}
                    onSave={(newName) => rename({ id: item.id, name: item.label }, newName)}
                    onCancel={() => (editingSourceId = null)}
                />
            {/snippet}
        </FilterList>
    </Segment>
{/if}
{#if deletingSource}
    <DeleteAnnotationSource
        {collectionId}
        source={deletingSource}
        onClose={() => (deletingSource = null)}
    />
{/if}
