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
        columnCount: number;
        itemCount: number;
        gridItem: Snippet<[{ index: number; style: string; width: number; height: number }]>;
        footerItem?: Snippet;
        viewportProps?: HTMLAttributes<HTMLDivElement>;
        gridProps?: Omit<
            ComponentProps<typeof VirtualGrid>,
            'itemHeight' | 'itemWidth' | 'height' | 'itemCount' | 'columnCount'
        >;
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

    let isReady = $state(false);
    $effect(() => {
        const timeout = setTimeout(() => {
            isReady = true;
        }, 1000);
        return () => clearTimeout(timeout);
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
                width: isLastInRow ? itemSize + GRID_GAP : itemSize,
                height: isLastRow ? itemSize + GRID_GAP : itemSize
            })}
        {/snippet}
        {#snippet footer()}
            {@render footerItem?.()}
        {/snippet}
    </VirtualGrid>
</div>
