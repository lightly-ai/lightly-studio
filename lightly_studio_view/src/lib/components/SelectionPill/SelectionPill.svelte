<script lang="ts">
    import { X } from '@lucide/svelte';
    import { fade, fly } from 'svelte/transition';
    import { usePillShortcuts } from '$lib/hooks/usePillShortcuts/usePillShortcuts';
    import type { GridType } from '$lib/types';
    import AnnotationsAnnotatePopover from './AnnotationsAnnotatePopover/AnnotationsAnnotatePopover.svelte';
    import ImagesAnnotatePopover from './ImagesAnnotatePopover/ImagesAnnotatePopover.svelte';
    import SelectionHint from './SelectionHint/SelectionHint.svelte';
    import { useSelectionHint } from './SelectionHint/useSelectionHint';
    import TagPopover from './TagPopover/TagPopover.svelte';

    interface Props {
        selectedCount: number;
        onClear: () => void;
        collectionId: string;
        gridType: GridType;
    }

    let { selectedCount, onClear, collectionId, gridType }: Props = $props();

    let tagOpen = $state(false);
    let annotateOpen = $state(false);
    const hasAnnotate = $derived(gridType === 'images' || gridType === 'annotations');
    const { tagKey, annotateKey } = usePillShortcuts();
    const { dismissed: hintDismissed, dismiss: dismissHint } = useSelectionHint();

    function isTyping(target: EventTarget | null) {
        const element = target instanceof HTMLElement ? target : null;
        return (
            element !== null &&
            (element.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName))
        );
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
            class="pointer-events-auto flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/90 px-4 py-2 text-primary-foreground shadow-lg backdrop-blur-sm"
        >
            <span class="whitespace-nowrap text-sm font-medium">
                {selectedCount} selected
            </span>
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
