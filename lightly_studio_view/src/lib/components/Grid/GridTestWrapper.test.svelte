<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import Grid from './Grid.svelte';

    let {
        itemCount = 20,
        columnCount = 3,
        scrollToIndex,
        scrollPosition,
        onScroll
    }: ComponentProps<typeof Grid> = $props();
</script>

<Grid {itemCount} {columnCount} {scrollToIndex} {scrollPosition} {onScroll}>
    {#snippet gridItem({ index, style, width, height })}
        <div data-testid="grid-item-{index}" data-width={width} data-height={height} {style}></div>
    {/snippet}
</Grid>
