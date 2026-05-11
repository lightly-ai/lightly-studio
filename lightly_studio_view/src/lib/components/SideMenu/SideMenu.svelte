<script lang="ts">
    import type { Annotation } from '$lib/types';
    import { type Readable } from 'svelte/store';
    import MenuItem from './MenuItem/MenuItem.svelte';

    interface Item {
        id: string;
        name: string;
        enabled: boolean;
    }

    interface SideMenuProps {
        items: Readable<Annotation[]>;
    }
    let { items }: SideMenuProps = $props();
</script>

<div class="width-full space-y-2 overflow-hidden">
    {#each $items as { id, name, enabled } (id)}
        <MenuItem
            {name}
            checked={enabled}
            onCheckedChange={() => {
                // Handle toggle logic here, e.g., update the store or call a function
            }}
        />
    {/each}
</div>
