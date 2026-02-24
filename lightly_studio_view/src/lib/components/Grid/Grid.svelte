<script lang="ts">
    import VirtualGrid from 'svelte-virtual/grid';
    import type { ComponentProps, Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';

    let viewport: HTMLElement | null = null;
    let clientWidth = $state(0);
    const GRID_GAP = 20;

    const {
        columnCount,
        itemCount,
        gridItem,
        footerItem,
        viewportProps,
        gridProps
    }: {
        /** Number of columns in the grid */
        columnCount: number;
        /** Total number of items to display */
        itemCount: number;
        /** Snippet to render each grid item. Receives index, style, width, and height */
        gridItem: Snippet<[{ index: number; style: string; width: number; height: number }]>;
        /** Optional snippet to render footer content */
        footerItem?: Snippet;
        /** Additional HTML attributes for the viewport div */
        viewportProps?: HTMLAttributes<HTMLDivElement>;
        /** Additional props to pass to the VirtualGrid component */
        gridProps?: Partial<ComponentProps<typeof VirtualGrid>>;
    } = $props();

    $effect(() => {
        if (viewport) {
            const resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    clientWidth = Math.max(entry.contentRect.width, 200);
                }
            });
            resizeObserver.observe(viewport);
            return () => resizeObserver.disconnect();
        }
    });

    let clientHeight = $state(0);
    const itemSize = $derived.by(() => {
        if (clientWidth === 0) {
            return 0;
        }
        return Math.floor(clientWidth / columnCount) - GRID_GAP;
    });
</script>

<div class="viewport h-full w-full" bind:this={viewport} bind:clientHeight {...viewportProps}>
    <VirtualGrid
        class="grid-scroll"
        itemHeight={itemSize + GRID_GAP}
        itemWidth={itemSize + GRID_GAP}
        height={clientHeight}
        {itemCount}
        {columnCount}
        {...gridProps}
    >
        {#snippet item({ index, style })}
            {@const isLastInRow = (index + 1) % columnCount === 0}
            {@const isLastRow = index >= itemCount - columnCount}
            {@render gridItem({
                index,
                style,
                width: itemSize,
                height: itemSize
            })}
        {/snippet}
        {#snippet footer()}
            {@render footerItem?.()}
        {/snippet}
    </VirtualGrid>
</div>

<style>
    .viewport {
        overflow-y: hidden;
    }
    .viewport :global(.grid-scroll) {
        overflow-x: hidden !important;
    }
</style>
