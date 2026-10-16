<script lang="ts">
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';
    import { projectAnnotations, projectPointCloud } from './projectionOverlay';

    interface Props {
        batch?: PointBatch;
        annotations: readonly AnnotationView[];
        projection?: CameraProjectionView;
    }

    let { batch, annotations, projection }: Props = $props();
    let canvas: HTMLCanvasElement | undefined = $state();

    $effect(() => {
        if (!canvas || !projection) return;
        canvas.width = projection.width;
        canvas.height = projection.height;
        const context = canvas.getContext('2d');
        if (!context) return;
        context.clearRect(0, 0, projection.width, projection.height);
        if (batch) {
            context.fillStyle = 'rgba(255, 255, 255, 0.8)';
            for (const point of projectPointCloud(batch, projection)) {
                context.fillRect(point.x - 1, point.y - 1, 2, 2);
            }
        }
        context.strokeStyle = '#ff5c5c';
        context.lineWidth = 2;
        context.beginPath();
        for (const segment of projectAnnotations(annotations, projection)) {
            context.moveTo(segment.start.x, segment.start.y);
            context.lineTo(segment.end.x, segment.end.y);
        }
        context.stroke();
    });
</script>

{#if projection}
    <canvas
        bind:this={canvas}
        class="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
    ></canvas>
{/if}
