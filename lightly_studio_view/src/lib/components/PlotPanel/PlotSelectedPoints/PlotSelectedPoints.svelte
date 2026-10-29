<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';

    interface Props {
        // Converts data coordinates to pixels. It changes on pan and zoom.
        proxy: OverlayProxy;
        x: Float32Array;
        y: Float32Array;
        category: Uint8Array;
        indices: number[];
        categoryColors: string[];
        radius: number;
    }

    let { proxy, x, y, category, indices, categoryColors, radius }: Props = $props();

    let canvas: HTMLCanvasElement | null = $state(null);

    // Draws the selected points again, larger and on top of the plot, so a small selection
    // stands out from the rest of the points.
    $effect(() => {
        const context = canvas?.getContext('2d');
        if (!canvas || !context) return;
        const pixelRatio = window.devicePixelRatio || 1;
        canvas.width = Math.round(proxy.width * pixelRatio);
        canvas.height = Math.round(proxy.height * pixelRatio);
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.clearRect(0, 0, proxy.width, proxy.height);
        for (const index of indices) {
            const { x: left, y: top } = proxy.location(x[index], y[index]);
            if (left < -radius || top < -radius) continue;
            if (left > proxy.width + radius || top > proxy.height + radius) continue;
            context.beginPath();
            context.arc(left, top, radius, 0, 2 * Math.PI);
            context.fillStyle = categoryColors[category[index]];
            context.fill();
        }
    });
</script>

<canvas
    bind:this={canvas}
    class="pointer-events-none absolute inset-0 h-full w-full"
    aria-hidden="true"
    data-testid="plot-selected-points"
></canvas>
