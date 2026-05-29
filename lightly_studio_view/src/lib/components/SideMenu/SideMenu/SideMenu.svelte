<script lang="ts">
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { type MenuItemType } from '../types';
    import type { HTMLAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils/shadcn';

    interface SideMenuProps {
        items: MenuItemType[];
        initialSelectedItemsIds?: string[];
        onChangeSelectedItems: (selectedItemsIds: string[]) => void;
        onColorChange?: (id: string, color: string) => void;
        containerProps?: HTMLAttributes<HTMLDivElement>;
        showColorMarker?: boolean;
    }

    let {
        items,
        initialSelectedItemsIds,
        onChangeSelectedItems,
        onColorChange,
        containerProps,
        showColorMarker
    }: SideMenuProps = $props();
    let selectedItemsIds = $state(initialSelectedItemsIds ?? []);

    const handleCheckedChange = (id: string) => {
        if (selectedItemsIds.includes(id)) {
            selectedItemsIds = selectedItemsIds.filter((itemId) => itemId !== id);
        } else {
            selectedItemsIds = [...selectedItemsIds, id];
        }
        onChangeSelectedItems(selectedItemsIds);
    };
</script>

<div {...containerProps} class={cn('w-full space-y-2 overflow-hidden', containerProps?.class)}>
    {#each items as { id, name, color } (id)}
        <MenuItem
            {name}
            {color}
            {showColorMarker}
            checked={selectedItemsIds.includes(id)}
            onCheckedChange={() => handleCheckedChange(id)}
            onColorChange={onColorChange ? (c) => onColorChange(id, c) : undefined}
        />
    {/each}
</div>
