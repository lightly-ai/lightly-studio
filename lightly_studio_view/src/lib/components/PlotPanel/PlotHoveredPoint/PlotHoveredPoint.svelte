<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';

    interface Props {
        // Converts data coordinates to pixels. It changes on pan and zoom.
        proxy: OverlayProxy;
        x: number;
        y: number;
    }

    let { proxy, x, y }: Props = $props();

    const location = $derived(proxy.location(x, y));
</script>

<!-- A ring around the point of the sample that is hovered in the grid. -->
<svg class="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
    <circle
        cx={location.x}
        cy={location.y}
        r="9"
        fill="none"
        stroke="black"
        stroke-width="4"
        stroke-opacity="0.7"
    />
    <circle
        cx={location.x}
        cy={location.y}
        r="9"
        fill="none"
        stroke="white"
        stroke-width="2"
        data-testid="plot-hovered-point"
    />
</svg>
