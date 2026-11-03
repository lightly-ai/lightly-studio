<script lang="ts">
    import { X } from '@lucide/svelte';
    import { fly } from 'svelte/transition';
    import type { GridType } from '$lib/types';
    import AnnotationsAnnotatePopover from './AnnotationsAnnotatePopover/AnnotationsAnnotatePopover.svelte';
    import ImagesAnnotatePopover from './ImagesAnnotatePopover/ImagesAnnotatePopover.svelte';
    import TagPopover from './TagPopover/TagPopover.svelte';

    interface Props {
        selectedCount: number;
        onClear: () => void;
        collectionId: string;
        gridType: GridType;
        /** Tag and Annotate only show in edit mode. */
        isEditing: boolean;
    }

    let { selectedCount, onClear, collectionId, gridType, isEditing }: Props = $props();

    let tagOpen = $state(false);
    let annotateOpen = $state(false);
</script>

{#if selectedCount > 0}
    <div
        class="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2"
        transition:fly={{ y: 20, duration: 200 }}
    >
        <div
            class="pointer-events-auto flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/90 px-4 py-2 text-primary-foreground shadow-lg backdrop-blur-sm"
        >
            <span class="text-sm font-medium">
                {selectedCount} selected
            </span>
            {#if isEditing}
                <TagPopover
                    {collectionId}
                    {gridType}
                    {selectedCount}
                    open={tagOpen}
                    onOpenChange={(open) => (tagOpen = open)}
                />
                {#if gridType === 'images'}
                    <ImagesAnnotatePopover
                        {collectionId}
                        {selectedCount}
                        open={annotateOpen}
                        onOpenChange={(open) => (annotateOpen = open)}
                    />
                {:else if gridType === 'annotations'}
                    <AnnotationsAnnotatePopover
                        {collectionId}
                        {selectedCount}
                        open={annotateOpen}
                        onOpenChange={(open) => (annotateOpen = open)}
                    />
                {/if}
            {/if}
            <button
                class="h-6.5 w-6.5 flex items-center justify-center rounded-full text-primary-foreground opacity-80 transition-[background-color,opacity,transform] duration-150 hover:scale-105 hover:bg-primary-foreground/10 hover:opacity-100"
                aria-label="Clear selection"
                onclick={onClear}
                data-testid="clear-selection-button"
            >
                <X class="h-4 w-4" />
            </button>
        </div>
    </div>
{/if}
