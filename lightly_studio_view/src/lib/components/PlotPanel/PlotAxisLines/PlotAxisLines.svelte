<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';

    interface Props {
        // Converts data coordinates to pixels. It changes on pan and zoom.
        proxy: OverlayProxy;
    }

    let { proxy }: Props = $props();

    // The pixel position of the origin. A line outside the plot is not drawn.
    const origin = $derived(proxy.location(0, 0));
    const isInPlot = (value: number, size: number) => value >= 0 && value <= size;
</script>

<!-- The lines at x = 0 and y = 0 split the plot into the four quadrants of the text axes. -->
<svg
    class="pointer-events-none absolute inset-0 h-full w-full stroke-white/40"
    stroke-width="1"
    stroke-dasharray="4 4"
    aria-hidden="true"
>
    {#if isInPlot(origin.x, proxy.width)}
        <line x1={origin.x} x2={origin.x} y1="0" y2={proxy.height} data-testid="plot-axis-line-x" />
    {/if}
    {#if isInPlot(origin.y, proxy.height)}
        <line x1="0" x2={proxy.width} y1={origin.y} y2={origin.y} data-testid="plot-axis-line-y" />
    {/if}
</svg>
