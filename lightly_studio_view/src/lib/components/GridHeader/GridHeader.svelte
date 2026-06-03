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

    // Drop button labels / the zoom slider as soon as the row stops fitting on one line; only
    // wrap onto a second row once even the compact layout overflows.
    let compact = $state(false);
    let wrap = $state(false);

    // Widths recorded at each transition so we can reverse it from clientWidth alone — once the
    // row wraps it no longer overflows, so scrollWidth can't tell us when to expand again.
    let compactThreshold = 0;
    let wrapThreshold = 0;

    function measure(el: HTMLDivElement): void {
        const overflows = el.scrollWidth > el.clientWidth;
        if (!compact) {
            if (overflows) {
                compactThreshold = el.scrollWidth;
                compact = true;
            }
        } else if (!wrap) {
            if (overflows) {
                wrapThreshold = el.scrollWidth;
                wrap = true;
            } else if (el.clientWidth >= compactThreshold) {
                compact = false;
            }
        } else if (el.clientWidth >= wrapThreshold) {
            wrap = false;
        }
    }

    $effect(() => {
        const el = barEl;
        if (!el) return;
        const observer = new ResizeObserver(() => measure(el));
        observer.observe(el);
        return () => observer.disconnect();
    });

    $effect(() => {
        // Compacting / wrapping resizes the bar's children, not the bar itself, so the
        // ResizeObserver won't fire again. Re-measure once the change has reflowed so the
        // full -> compact -> wrap sequence can complete within a single resize. The machine
        // is monotonic per direction, so this converges (a settled measure changes nothing).
        void compact;
        void wrap;
        const el = barEl;
        if (!el) return;
        const frame = requestAnimationFrame(() => measure(el));
        return () => cancelAnimationFrame(frame);
    });
</script>

<div
    bind:this={barEl}
    class="my-2 flex min-w-0 items-center gap-x-4 gap-y-2"
    class:flex-nowrap={!wrap}
    class:flex-wrap={wrap}
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
