<script lang="ts">
    import { untrack, type Snippet } from 'svelte';
    import type { HTMLAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils';
    import {
        buildJustifiedRows,
        getJustifiedContentHeight,
        getVisibleRowRange
    } from './justifiedRows';

    interface Props {
        /** Width / height per item, in item order. Missing entries fall back to square. */
        aspectRatios: number[];
        /**
         * How many tiles a row holds at a square aspect ratio. The pre-justification row height
         * follows from the measured container, so the same zoom setting stays usable in a
         * narrow pane instead of ballooning to one huge tile per row.
         */
        columnCount: number;
        gap?: number;
        gridItem: Snippet<[{ index: number; width: number; height: number }]>;
        footerItem?: Snippet;
        /** Extra rows rendered above and below the viewport. */
        overScan?: number;
        onScroll?: (event: Event) => void;
        initialScrollPosition?: number;
        /** Resets scroll position to top when this key changes. */
        scrollResetKey?: string;
        gridProps?: HTMLAttributes<HTMLDivElement>;
    }

    const {
        aspectRatios,
        columnCount,
        gap = 10,
        gridItem,
        footerItem,
        overScan = 3,
        onScroll,
        initialScrollPosition,
        scrollResetKey,
        gridProps
    }: Props = $props();

    let scroller = $state<HTMLDivElement>();
    let containerWidth = $state(0);
    let viewportHeight = $state(0);
    let scrollTop = $state(0);

    const targetRowHeight = $derived(containerWidth / Math.max(1, columnCount));
    const rows = $derived(
        buildJustifiedRows({ aspectRatios, containerWidth, targetRowHeight, gap })
    );
    const contentHeight = $derived(getJustifiedContentHeight(rows));
    const range = $derived(
        getVisibleRowRange({ rows, scrollTop, viewportHeight, overscan: overScan })
    );
    const visibleRows = $derived(rows.slice(range.start, range.end + 1));

    $effect(() => {
        const el = scroller;
        if (!el) return;
        const observer = new ResizeObserver(([entry]) => {
            containerWidth = entry.contentRect.width;
            viewportHeight = entry.contentRect.height;
        });
        observer.observe(el);
        return () => observer.disconnect();
    });

    function handleScroll(event: Event) {
        scrollTop = (event.target as HTMLElement).scrollTop;
        onScroll?.(event);
    }

    let previousScrollResetKey = $state(untrack(() => scrollResetKey));
    let previousInitialScrollPosition = $state<number | undefined>(undefined);

    $effect(() => {
        if (scrollResetKey === previousScrollResetKey) return;
        previousScrollResetKey = scrollResetKey;
        // Treat the pending restore as already applied, or it would immediately scroll back.
        previousInitialScrollPosition = initialScrollPosition ?? undefined;
        scroller?.scrollTo({ top: 0 });
    });

    $effect(() => {
        if (!scroller || contentHeight <= 0 || initialScrollPosition == null) return;
        if (previousInitialScrollPosition === initialScrollPosition) return;
        previousInitialScrollPosition = initialScrollPosition;
        scroller.scrollTo({ top: initialScrollPosition });
    });
</script>

<div
    bind:this={scroller}
    {...gridProps}
    class={cn('h-full w-full overflow-y-auto overflow-x-hidden', gridProps?.class)}
    onscroll={handleScroll}
>
    <div class="relative w-full" style="height: {contentHeight}px;">
        {#each visibleRows as row (row.top)}
            <div
                class="absolute left-0 flex w-full"
                style="top: {row.top}px; height: {row.height}px; gap: {gap}px;"
            >
                {#each row.tiles as tile (tile.index)}
                    <div class="flex-none" style="width: {tile.width}px; height: {tile.height}px;">
                        {@render gridItem({
                            index: tile.index,
                            width: tile.width,
                            height: tile.height
                        })}
                    </div>
                {/each}
            </div>
        {/each}
    </div>
    {@render footerItem?.()}
</div>
