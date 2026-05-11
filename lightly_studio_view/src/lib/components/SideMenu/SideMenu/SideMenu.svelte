<script lang="ts">
    import { type Readable } from 'svelte/store';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { type MenuItemType } from '../types';
    import type { HTMLAttributes } from 'svelte/elements';

    interface SideMenuProps {
        items: Readable<MenuItemType[]>;
        initialSelectedItemsIds?: Readable<string[]>;
        onChangeSelectedItems: (selectedItemsIds: string[]) => void;
        containerProps?: HTMLAttributes<HTMLDivElement>;
        showColorMarker?: boolean;
    }

    let {
        items,
        initialSelectedItemsIds,
        onChangeSelectedItems,
        containerProps,
        showColorMarker
    }: SideMenuProps = $props();
    let selectedItemsIds = $derived($initialSelectedItemsIds || []);

    const handleCheckedChange = (id: string) => {
        if (selectedItemsIds.includes(id)) {
            selectedItemsIds = selectedItemsIds.filter((itemId) => itemId !== id);
        } else {
            selectedItemsIds = [...selectedItemsIds, id];
        }
        onChangeSelectedItems?.(selectedItemsIds);
    };
</script>

<div {...containerProps} class="w-full space-y-2 overflow-hidden">
    {#each $items as { id, name } (id)}
        <MenuItem
            {name}
            {showColorMarker}
            checked={selectedItemsIds.includes(id)}
            onCheckedChange={() => handleCheckedChange(id)}
        />
    {/each}
</div>
