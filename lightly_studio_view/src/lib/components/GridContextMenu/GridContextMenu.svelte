<script lang="ts">
    import type { Snippet } from 'svelte';
    import * as ContextMenu from '$lib/components/ui/context-menu/index.js';
    import GridContextMenuTagList from './GridContextMenuTagList.svelte';

    interface Props {
        /** The grid viewport the menu is opened from. */
        children: Snippet;
        /** File name of the clicked sample, or "N samples" for a selection. */
        headerLabel: string;
        tags: Array<{ tag_id: string; name: string }>;
        tagStates: Record<string, 'checked' | 'indeterminate' | 'unchecked'>;
        knownTargetNote?: string;
        canEditTags: boolean;
        busy: boolean;
        hasSelection: boolean;
        /** Resolves the clicked sample; returning false keeps the menu closed. */
        onResolveTarget: (event: MouseEvent) => boolean;
        onToggleTag: (tagId: string) => void;
        onCreateAndAssign: (name: string) => void;
        onOpen: () => void;
        onFindSimilar: () => void;
        onClearSelection: () => void;
    }

    let {
        children,
        headerLabel,
        tags,
        tagStates,
        knownTargetNote,
        canEditTags,
        busy,
        hasSelection,
        onResolveTarget,
        onToggleTag,
        onCreateAndAssign,
        onOpen,
        onFindSimilar,
        onClearSelection
    }: Props = $props();

    let open = $state(false);

    function handleContextMenu(event: MouseEvent) {
        if (onResolveTarget(event)) return;
        // bits-ui opens on its own merged handler, so a right-click that hit no tile is
        // closed again on the next tick instead of being vetoed here.
        queueMicrotask(() => {
            open = false;
        });
    }

    // Grid cells recycle as the virtualized list scrolls, so an open menu must not
    // linger over unrelated tiles. Capture catches the grid's inner scroll container.
    $effect(() => {
        if (!open) return;

        const close = () => {
            open = false;
        };
        window.addEventListener('scroll', close, { capture: true, passive: true });
        window.addEventListener('resize', close);

        return () => {
            window.removeEventListener('scroll', close, { capture: true });
            window.removeEventListener('resize', close);
        };
    });
</script>

<ContextMenu.Root bind:open>
    <ContextMenu.Trigger oncontextmenu={handleContextMenu}>
        {#snippet child({ props })}
            <div {...props} class="h-full w-full">
                {@render children()}
            </div>
        {/snippet}
    </ContextMenu.Trigger>
    <ContextMenu.Content class="w-56" data-testid="grid-context-menu">
        <ContextMenu.Group>
            <ContextMenu.GroupHeading class="truncate" data-testid="grid-context-menu-header">
                {headerLabel}
            </ContextMenu.GroupHeading>
        </ContextMenu.Group>
        {#if canEditTags}
            <ContextMenu.Sub>
                <ContextMenu.SubTrigger data-testid="grid-context-menu-tags">
                    Tags
                </ContextMenu.SubTrigger>
                <ContextMenu.SubContent class="w-56 p-0">
                    <GridContextMenuTagList
                        {tags}
                        {tagStates}
                        {busy}
                        {knownTargetNote}
                        onToggle={onToggleTag}
                        onCreate={onCreateAndAssign}
                    />
                </ContextMenu.SubContent>
            </ContextMenu.Sub>
            <ContextMenu.Separator />
        {/if}
        <ContextMenu.Item onSelect={onOpen} data-testid="grid-context-menu-open">
            Open
        </ContextMenu.Item>
        <ContextMenu.Item onSelect={onFindSimilar} data-testid="grid-context-menu-find-similar">
            Find similar images
        </ContextMenu.Item>
        {#if hasSelection}
            <ContextMenu.Separator />
            <ContextMenu.Item
                onSelect={onClearSelection}
                data-testid="grid-context-menu-clear-selection"
            >
                Clear selection
            </ContextMenu.Item>
        {/if}
    </ContextMenu.Content>
</ContextMenu.Root>
