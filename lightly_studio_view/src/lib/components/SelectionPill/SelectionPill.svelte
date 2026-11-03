<script lang="ts">
    import { X } from '@lucide/svelte';
    import { fade, fly } from 'svelte/transition';
    import { GRID_IMAGE_SEARCH_DROP_EVENT, type GridItemDragData } from '$lib/components/GridItem';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { usePillShortcuts } from '$lib/hooks/usePillShortcuts/usePillShortcuts';
    import { getSelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';
    import type { GridType } from '$lib/types';
    import { getImageURL } from '$lib/utils/getImageURL';
    import AnnotationsAnnotatePopover from './AnnotationsAnnotatePopover/AnnotationsAnnotatePopover.svelte';
    import ImagesAnnotatePopover from './ImagesAnnotatePopover/ImagesAnnotatePopover.svelte';
    import SelectionHint from './SelectionHint/SelectionHint.svelte';
    import { useSelectionHint } from './SelectionHint/useSelectionHint';
    import SelectionMoreMenu from './SelectionMoreMenu/SelectionMoreMenu.svelte';
    import SelectionThumbnails from './SelectionThumbnails/SelectionThumbnails.svelte';
    import TagPopover from './TagPopover/TagPopover.svelte';
    import {
        canOfferSelectAll,
        getSelectionThumbnailURLs,
        isTyping
    } from './selectionPill.helpers';

    interface Props {
        selectedCount: number;
        onClear: () => void;
        collectionId: string;
        gridType: GridType;
        /** How many items the grid shows with its filters (the footer count). */
        gridTotal?: number;
        /** Selects every item of the grid, like the grid's "Select all". */
        onSelectAll?: () => void;
        /** The collection has image embeddings, so "Find similar images" can run. */
        canSearchSimilar?: boolean;
    }

    let {
        selectedCount,
        onClear,
        collectionId,
        gridType,
        gridTotal = 0,
        onSelectAll,
        canSearchSimilar = false
    }: Props = $props();

    let tagOpen = $state(false);
    let annotateOpen = $state(false);
    const hasAnnotate = $derived(gridType === 'images' || gridType === 'annotations');
    const { tagKey, annotateKey } = usePillShortcuts();
    const { dismissed: hintDismissed, dismiss: dismissHint } = useSelectionHint();
    const { getSelectedSampleIds } = useGlobalStorage();
    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));

    // Reading selectedCount makes the target follow the selection.
    const target = $derived.by(() => {
        void selectedCount;
        return getSelectionTarget(collectionId, gridType);
    });
    const thumbnailURLs = $derived(getSelectionThumbnailURLs(gridType, $selectedSampleIds));
    const showSelectAll = $derived(
        onSelectAll !== undefined && canOfferSelectAll(target, selectedCount, gridTotal)
    );
    const selectedIds = $derived(target.kind === 'ids' ? target.ids : null);
    const similarSourceId = $derived(
        canSearchSimilar && gridType === 'images' && selectedIds?.length === 1
            ? selectedIds[0]
            : null
    );

    // Reuses the grid's drag-to-search path, so the search bar shows the image as its query.
    function findSimilar() {
        if (!similarSourceId) return;
        const detail: GridItemDragData = {
            url: getImageURL(similarSourceId),
            fileName: 'Selected image'
        };
        window.dispatchEvent(new CustomEvent(GRID_IMAGE_SEARCH_DROP_EVENT, { detail }));
    }

    // Lives here, so only collection grids hear T and L; sample details owns its own keys.
    function handleKeydown(event: KeyboardEvent) {
        if (selectedCount === 0 || event.repeat) return;
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        if (isTyping(event.target) || isTyping(document.activeElement)) return;
        const key = event.key.toLowerCase();
        if (key === $tagKey.toLowerCase()) {
            event.preventDefault();
            annotateOpen = false;
            tagOpen = true;
        } else if (hasAnnotate && key === $annotateKey.toLowerCase()) {
            event.preventDefault();
            tagOpen = false;
            annotateOpen = true;
        }
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if selectedCount > 0}
    <div
        class="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2"
        transition:fly={{ y: 20, duration: 200 }}
    >
        <div
            class="pointer-events-auto flex items-center gap-2 rounded-xl border-2 border-primary/60 bg-card py-2 pl-3 pr-2 text-card-foreground shadow-xl"
            data-testid="selection-pill"
        >
            <SelectionThumbnails urls={thumbnailURLs} />
            <span class="whitespace-nowrap text-sm font-semibold">
                {selectedCount.toLocaleString()} selected
            </span>
            {#if showSelectAll}
                <button
                    class="whitespace-nowrap text-sm font-medium text-primary underline-offset-2 hover:underline"
                    onclick={() => onSelectAll?.()}
                >
                    Select all {gridTotal.toLocaleString()}
                </button>
            {/if}
            <span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>
            <TagPopover
                {collectionId}
                {gridType}
                {selectedCount}
                open={tagOpen}
                onOpenChange={(open) => (tagOpen = open)}
                shortcutHint={$tagKey}
            />
            {#if gridType === 'images'}
                <ImagesAnnotatePopover
                    {collectionId}
                    {selectedCount}
                    open={annotateOpen}
                    onOpenChange={(open) => (annotateOpen = open)}
                    shortcutHint={$annotateKey}
                />
            {:else if gridType === 'annotations'}
                <AnnotationsAnnotatePopover
                    {collectionId}
                    {selectedCount}
                    open={annotateOpen}
                    onOpenChange={(open) => (annotateOpen = open)}
                    shortcutHint={$annotateKey}
                />
            {/if}
            <SelectionMoreMenu
                ids={selectedIds}
                onFindSimilar={similarSourceId ? findSimilar : undefined}
            />
            <button
                class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                aria-label="Clear selection"
                onclick={onClear}
                data-testid="clear-selection-button"
            >
                <X class="h-4 w-4" />
            </button>
        </div>
    </div>
{:else if !$hintDismissed}
    <div
        class="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2"
        transition:fade={{ duration: 150 }}
    >
        <SelectionHint
            {gridType}
            tagKey={$tagKey}
            annotateKey={hasAnnotate ? $annotateKey : undefined}
            onDismiss={dismissHint}
        />
    </div>
{/if}
