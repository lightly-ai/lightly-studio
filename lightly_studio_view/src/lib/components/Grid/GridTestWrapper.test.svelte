<script lang="ts">
    import Grid from './Grid.svelte';

    let {
        itemCount = 20,
        columnCount = 3,
        overScan,
        overscan,
        onScroll,
        initialScrollPosition,
        scrollResetKey
    }: {
        itemCount?: number;
        columnCount?: number;
        overScan?: number;
        overscan?: number;
        onScroll?: (event: Event) => void;
        initialScrollPosition?: number;
        scrollResetKey?: string;
    } = $props();
</script>

<Grid
    {itemCount}
    {columnCount}
    {overScan}
    {overscan}
    {onScroll}
    {initialScrollPosition}
    {scrollResetKey}
    gridProps={{ 'data-testid': 'grid' }}
>
    {#snippet gridItem({ index, style, width, height })}
        <div data-testid="grid-item-{index}" data-width={width} data-height={height} {style}></div>
    {/snippet}

    {#snippet footerItem()}
        <div data-testid="grid-footer">Footer</div>
    {/snippet}
</Grid>
