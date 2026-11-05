<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';

    interface Props {
        markers: { label: string; x: number; y: number }[];
        proxy: OverlayProxy;
    }

    let { markers, proxy }: Props = $props();

    // The library makes a new proxy for each viewport change, so the markers move with pan and
    // zoom. A marker outside the plot is not shown.
    const visibleMarkers = $derived(
        markers
            .map((marker) => ({ label: marker.label, ...proxy.location(marker.x, marker.y) }))
            .filter(({ x, y }) => x >= 0 && x <= proxy.width && y >= 0 && y <= proxy.height)
    );
</script>

<div class="pointer-events-none absolute inset-0 z-10" data-testid="plot-markers">
    {#each visibleMarkers as marker (marker.label)}
        <!-- A zero-size anchor at the marker position: the dot is centered on it and the label
             starts to its right, so a long label does not move the dot. -->
        <div class="absolute" style="left: {marker.x}px; top: {marker.y}px">
            <div
                class="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-black bg-amber-400"
            ></div>
            <span
                class="absolute left-2.5 top-0 -translate-y-1/2 whitespace-nowrap text-xs font-medium text-white [text-shadow:0_0_2px_#000,0_0_2px_#000]"
            >
                {marker.label}
            </span>
        </div>
    {/each}
</div>
