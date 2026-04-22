<script lang="ts">
    import VirtualGrid from 'svelte-virtual/grid';
    import type { ComponentProps, Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils';

    const GRID_GAP = 16;

    let viewport: HTMLElement | null = null;
    let clientWidth = $state(0);
    let clientHeight = $state(0);
    let grid: ReturnType<typeof VirtualGrid> | undefined = $state();

    let {
        columnCount,
        itemCount,
        gridItem,
        footerItem,
        overScan,
        overscan,
        onScroll,
        initialScrollPosition,
        scrollResetKey,
        viewportProps,
        gridProps
    }: {
        /** Number of columns in the grid */
        columnCount: number;
        /** Total number of items to display */
        itemCount: number;
        /** Snippet to render each grid item */
        gridItem: Snippet<[{ index: number; style: string; width: number; height: number }]>;
        /** Optional snippet to render footer content */
        footerItem?: Snippet;
        /** Number of rows to render outside the visible area */
        overScan?: number;
        /** Alias for overScan */
        overscan?: number;
        /** Scroll event callback */
        onScroll?: (event: Event) => void;
        /** Initial vertical scroll position */
        initialScrollPosition?: number;
        /** Resets scroll position to top when this key changes */
        scrollResetKey?: string;
        /** Additional HTML attributes for the viewport div */
        viewportProps?: HTMLAttributes<HTMLDivElement>;
        /** Additional props to pass to the VirtualGrid component */
        gridProps?: Partial<ComponentProps<typeof VirtualGrid>>;
    } = $props();

    let previousScrollResetKey = scrollResetKey;
    let previousInitialScrollPosition = $state<number | undefined>(undefined);

    const safeColumnCount = $derived(Math.max(1, columnCount));

    const viewportClassName = $derived(cn('viewport h-full w-full', viewportProps?.class));

    const gridClassName = $derived(cn('grid-scroll', gridProps?.class));

    const resolvedOverScan = $derived(overScan ?? overscan ?? gridProps?.overScan);

    const resolvedOnScroll = $derived(onScroll ?? gridProps?.onscroll);

    $effect(() => {
        if (!viewport) {
            return;
        }

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                clientWidth = Math.max(entry.contentRect.width, 200);
            }
        });

        resizeObserver.observe(viewport);

        return () => resizeObserver.disconnect();
    });

    const cellSize = $derived.by(() => {
        if (clientWidth === 0) {
            return 0;
        }

        return Math.max(1, Math.floor(clientWidth / safeColumnCount));
    });

    const itemSize = $derived(Math.max(1, cellSize - GRID_GAP));

    $effect(() => {
        if (scrollResetKey === previousScrollResetKey) {
            return;
        }

        previousScrollResetKey = scrollResetKey;
        // Mark the current initialScrollPosition as already applied so the
        // restore effect does not immediately scroll back after the reset.
        previousInitialScrollPosition = initialScrollPosition ?? undefined;
        grid?.scrollToPosition(0);
    });

    $effect(() => {
        if (
            !grid ||
            cellSize <= 0 ||
            initialScrollPosition === undefined ||
            initialScrollPosition === null
        ) {
            return;
        }

        if (previousInitialScrollPosition === initialScrollPosition) {
            return;
        }

        previousInitialScrollPosition = initialScrollPosition;

        requestAnimationFrame(() => {
            grid?.scrollToPosition(initialScrollPosition);
        });
    });
</script>

<div bind:this={viewport} bind:clientHeight {...viewportProps} class={viewportClassName}>
    <VirtualGrid
        bind:this={grid}
        {...gridProps}
        class={gridClassName}
        itemHeight={cellSize}
        itemWidth={cellSize}
        height={clientHeight}
        {itemCount}
        columnCount={safeColumnCount}
        overScan={resolvedOverScan}
        onscroll={resolvedOnScroll}
    >
        {#snippet item({ index, style })}
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
