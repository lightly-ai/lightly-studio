<script lang="ts">
    import { untrack, type Snippet } from 'svelte';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { type MenuItemType } from '../types';
    import type { HTMLAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils/shadcn';

    interface SideMenuProps {
        items: MenuItemType[];
        /** Uncontrolled: seeds the selection once on mount. */
        initialSelectedItemsIds?: string[];
        /** Controlled: when provided, the checkboxes track this value reactively. */
        selectedItemsIds?: string[];
        onChangeSelectedItems: (selectedItemsIds: string[]) => void;
        containerProps?: HTMLAttributes<HTMLDivElement>;
        showColorMarker?: boolean;
        /** When `true`, color swatches open a color picker on click. */
        enableColorPicker?: boolean;
        rowAction?: Snippet<[MenuItemType]>;
    }

    let {
        items,
        initialSelectedItemsIds,
        selectedItemsIds,
        onChangeSelectedItems,
        containerProps,
        showColorMarker,
        enableColorPicker,
        rowAction
    }: SideMenuProps = $props();

    let internalSelectedItemsIds = $state(untrack(() => initialSelectedItemsIds ?? []));
    const selected = $derived(selectedItemsIds ?? internalSelectedItemsIds);

    const handleCheckedChange = (id: string) => {
        const next = selected.includes(id)
            ? selected.filter((itemId) => itemId !== id)
            : [...selected, id];
        // Only own the state when uncontrolled; otherwise the parent drives `selected`.
        if (selectedItemsIds === undefined) {
            internalSelectedItemsIds = next;
        }
        onChangeSelectedItems(next);
    };
</script>

<div {...containerProps} class={cn('w-full space-y-2 overflow-hidden', containerProps?.class)}>
    {#each items as { id, name } (id)}
        <div class="flex min-w-0 items-center gap-1">
            <div class="min-w-0 flex-1">
                <MenuItem
                    {name}
                    {showColorMarker}
                    {enableColorPicker}
                    checked={selected.includes(id)}
                    onCheckedChange={() => handleCheckedChange(id)}
                />
            </div>
            {@render rowAction?.({ id, name })}
        </div>
    {/each}
</div>
