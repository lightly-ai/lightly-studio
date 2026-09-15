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
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import DeleteSourceDialog from './DeleteSourceDialog.svelte';
    import ConfidenceFilter from './ConfidenceFilter.svelte';

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

    const isEnabled = $derived(items.length > 0);
    let sourceToDelete = $state<{ id: string; name: string } | null>(null);

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
        >
            {#snippet rowAction(item)}
                <Button
                    variant="ghost"
                    size="icon"
                    class="size-7 shrink-0"
                    title={`Delete ${item.name}`}
                    aria-label={`Delete annotation source ${item.name}`}
                    onclick={() => (sourceToDelete = item)}
                >
                    <Trash2 class="size-3.5" />
                </Button>
            {/snippet}
        </SideMenu>
    </Segment>
    <ConfidenceFilter />
{/if}

{#if sourceToDelete}
    <DeleteSourceDialog source={sourceToDelete} onClose={() => (sourceToDelete = null)} />
{/if}
