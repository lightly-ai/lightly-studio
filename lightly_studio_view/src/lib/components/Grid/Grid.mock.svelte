<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        itemCount: number;
        columnCount?: number;
        gridItem: Snippet<[{ index: number; style: string; width: number; height: number }]>;
        footerItem?: Snippet;
        [key: string]: unknown;
    }

    let { itemCount, gridItem, footerItem }: Props = $props();
</script>

{#each Array.from({ length: itemCount }, (_, i) => i) as index}
    {@render gridItem({ index, style: '', width: 200, height: 150 })}
{/each}
{#if footerItem}
    {@render footerItem()}
{/if}
