<script lang="ts">
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
    }

    let {
        items,
        initialSelectedItemsIds,
        selectedItemsIds,
        onChangeSelectedItems,
        containerProps,
        showColorMarker,
        enableColorPicker
    }: SideMenuProps = $props();

    let internalSelectedItemsIds = $state(initialSelectedItemsIds ?? []);
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
        <MenuItem
            {name}
            {showColorMarker}
            {enableColorPicker}
            checked={selected.includes(id)}
            onCheckedChange={() => handleCheckedChange(id)}
        />
    {/each}
</div>
