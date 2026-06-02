<script lang="ts">
    import type { Snippet } from 'svelte';
    import { ImageSizeControl } from '$lib/components';

    interface GridHeaderProps {
        showImageSizeControl?: boolean;
        children?: Snippet;
        // The snippets receive whether the toolbar is currently compact, so the
        // controls they render can drop their text labels when space runs out.
        selectionControls?: Snippet<[boolean]>;
        auxControls?: Snippet<[boolean]>;
    }

    let {
        showImageSizeControl = true,
        children,
        selectionControls,
        auxControls
    }: GridHeaderProps = $props();

    let barEl = $state<HTMLDivElement | null>(null);
    let compact = $state(false);
    // The width the toolbar needs to show every control with its labels. It is
    // captured from scrollWidth while the (expanded) bar is overflowing, then used
    // as a stable threshold for re-expanding — so toggling compact can't oscillate.
    let expandedWidth = 0;

    function measure(el: HTMLDivElement) {
        if (!compact) {
            // Collapse the moment the full-width layout no longer fits.
            if (el.scrollWidth > el.clientWidth) {
                expandedWidth = el.scrollWidth;
                compact = true;
            }
        } else if (expandedWidth > 0 && el.clientWidth >= expandedWidth) {
            // Re-expand only once the full layout is known to fit again.
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

<div bind:this={barEl} class="my-2 flex items-center space-x-4">
    <div class="min-w-0 flex-1">
        {@render children?.()}
    </div>

    {@render selectionControls?.(compact)}
    {#if showImageSizeControl}
        <ImageSizeControl {compact} />
    {/if}
    {@render auxControls?.(compact)}
</div>
