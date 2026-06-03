<script lang="ts">
    import type { Snippet } from 'svelte';
    import { ImageSizeControl } from '$lib/components';

    interface GridHeaderProps {
        showImageSizeControl?: boolean;
        children?: Snippet;
        selectionControls?: Snippet<[boolean]>;
        auxControls?: Snippet<[boolean]>;
    }

    let {
        showImageSizeControl = true,
        children,
        selectionControls,
        auxControls
    }: GridHeaderProps = $props();

    let barEl = $state<HTMLDivElement>();

    // Drop button labels / the zoom slider once the full row stops fitting on one line. While
    // compact the row is allowed to wrap, so CSS spills it onto a second row only if even the
    // compacted controls overflow.
    let compact = $state(false);

    // The full-layout width that triggered compaction, recorded while the row was flex-nowrap
    // (the only state where overflow is observable). We re-expand once the bar is at least this
    // wide again — using the threshold instead of a live measurement, since a wrapped row never
    // reports overflow.
    let compactThreshold = 0;

    function measure(el: HTMLDivElement): void {
        if (!compact) {
            if (el.scrollWidth > el.clientWidth) {
                compactThreshold = el.scrollWidth;
                compact = true;
            }
        } else if (el.clientWidth >= compactThreshold) {
            compact = false;
        }
    }

    $effect(() => {
        const el = barEl;
        if (!el) return;
        const observer = new ResizeObserver(() => measure(el));
        observer.observe(el);
        return () => observer.disconnect();
    });
</script>

<div
    bind:this={barEl}
    class="my-2 flex min-w-0 items-center gap-x-4 gap-y-2"
    class:flex-nowrap={!compact}
    class:flex-wrap={compact}
>
    {#if children}
        <div class="min-w-[12rem] flex-1">
            {@render children()}
        </div>
    {:else}
        <div class="flex-1"></div>
    {/if}

    {@render selectionControls?.(compact)}
    {#if showImageSizeControl}
        <ImageSizeControl {compact} />
    {/if}
    {@render auxControls?.(compact)}
</div>
