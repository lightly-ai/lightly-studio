<script lang="ts">
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';
    import { drawProjectionOverlay, type AnnotationClassColor } from './projectionOverlay';
    import { DEFAULT_PROJECTION_SETTINGS, type ProjectionSettings } from './projectionSettings';

    interface Props {
        batch?: PointBatch;
        annotations: readonly AnnotationView[];
        annotationClasses?: readonly AnnotationClassColor[];
        projection?: CameraProjectionView;
        settings?: ProjectionSettings;
    }

    let {
        batch,
        annotations,
        annotationClasses = [],
        projection,
        settings = DEFAULT_PROJECTION_SETTINGS
    }: Props = $props();
    let canvas: HTMLCanvasElement | undefined = $state();

    $effect(() => {
        if (!canvas || !projection) return;
        canvas.width = projection.width;
        canvas.height = projection.height;
        const context = canvas.getContext('2d');
        if (!context) return;
        drawProjectionOverlay(context, projection, batch, annotations, settings, annotationClasses);
    });
</script>

{#if projection}
    <canvas
        bind:this={canvas}
        class="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
    ></canvas>
{/if}
