<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';
    import { getAxisLinePositions } from './axisLinePositions';

    interface Props {
        // Converts data coordinates to pixels. It changes on pan and zoom.
        proxy: OverlayProxy;
    }

    let { proxy }: Props = $props();

    const positions = $derived(getAxisLinePositions(proxy));
</script>

<!-- The lines at x = 0 and y = 0 split the plot into the four quadrants of the text axes. -->
<svg
    class="pointer-events-none absolute inset-0 h-full w-full stroke-white/40"
    stroke-width="1"
    stroke-dasharray="4 4"
    aria-hidden="true"
>
    {#if positions.x !== null}
        <line
            x1={positions.x}
            x2={positions.x}
            y1="0"
            y2={proxy.height}
            data-testid="plot-axis-line-x"
        />
    {/if}
    {#if positions.y !== null}
        <line
            x1="0"
            x2={proxy.width}
            y1={positions.y}
            y2={positions.y}
            data-testid="plot-axis-line-y"
        />
    {/if}
</svg>
