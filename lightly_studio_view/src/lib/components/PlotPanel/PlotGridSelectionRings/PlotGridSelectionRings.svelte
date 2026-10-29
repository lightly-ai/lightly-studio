<script lang="ts">
    import type { OverlayProxy } from 'embedding-atlas/svelte';

    interface Props {
        // Converts data coordinates to pixels. It changes on pan and zoom.
        proxy: OverlayProxy;
        x: Float32Array;
        y: Float32Array;
        indices: number[];
    }

    let { proxy, x, y, indices }: Props = $props();

    const RING_RADIUS = 9;

    let canvas: HTMLCanvasElement | null = $state(null);

    // A ring around the point of each sample selected in the grid: a dark halo under a white
    // line, so it shows on both light and dark points.
    $effect(() => {
        const context = canvas?.getContext('2d');
        if (!canvas || !context) return;
        const pixelRatio = window.devicePixelRatio || 1;
        canvas.width = Math.round(proxy.width * pixelRatio);
        canvas.height = Math.round(proxy.height * pixelRatio);
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.clearRect(0, 0, proxy.width, proxy.height);
        const path = new Path2D();
        for (const index of indices) {
            const { x: left, y: top } = proxy.location(x[index], y[index]);
            if (left < -RING_RADIUS || top < -RING_RADIUS) continue;
            if (left > proxy.width + RING_RADIUS || top > proxy.height + RING_RADIUS) continue;
            path.moveTo(left + RING_RADIUS, top);
            path.arc(left, top, RING_RADIUS, 0, 2 * Math.PI);
        }
        context.lineWidth = 4;
        context.strokeStyle = 'rgba(0, 0, 0, 0.7)';
        context.stroke(path);
        context.lineWidth = 2;
        context.strokeStyle = 'white';
        context.stroke(path);
    });
</script>

<canvas
    bind:this={canvas}
    class="pointer-events-none absolute inset-0 h-full w-full"
    aria-hidden="true"
    data-testid="plot-grid-selection-rings"
></canvas>
