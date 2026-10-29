<script lang="ts">
    import { untrack } from 'svelte';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { type MenuItemType } from '../types';
    import type { Snippet } from 'svelte';
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
        /** Renders controls at the end of each item row, e.g. a delete button. */
        itemActions?: Snippet<[MenuItemType]>;
        /** The item whose row shows `itemEditor` instead of its label, e.g. while renaming. */
        editingItemId?: string | null;
        itemEditor?: Snippet<[MenuItemType, { checked: boolean; onCheckedChange: () => void }]>;
    }

    let {
        items,
        initialSelectedItemsIds,
        selectedItemsIds,
        onChangeSelectedItems,
        containerProps,
        showColorMarker,
        enableColorPicker,
        itemActions,
        editingItemId = null,
        itemEditor
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
    {#each items as item (item.id)}
        {#if item.id === editingItemId && itemEditor}
            {@render itemEditor(item, {
                checked: selected.includes(item.id),
                onCheckedChange: () => handleCheckedChange(item.id)
            })}
        {:else}
            <MenuItem
                name={item.name}
                {showColorMarker}
                {enableColorPicker}
                checked={selected.includes(item.id)}
                onCheckedChange={() => handleCheckedChange(item.id)}
            >
                {#snippet actions()}
                    {@render itemActions?.(item)}
                {/snippet}
            </MenuItem>
        {/if}
    {/each}
</div>
