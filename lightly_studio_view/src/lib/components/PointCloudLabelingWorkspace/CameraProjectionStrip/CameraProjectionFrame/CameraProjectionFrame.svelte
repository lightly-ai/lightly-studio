<script lang="ts">
    import Camera from '@lucide/svelte/icons/camera';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import type { ProjectionSettings } from '../projectionSettings';
    import type { AnnotationClassColor } from '../projectionOverlay';
    import { useCameraFrame } from './useCameraFrame/useCameraFrame.svelte';
    interface Props {
        datasetId: string;
        recordingId?: string;
        channelId: number;
        keyframeTimestampNs?: string;
        logTimeNs?: string;
        blob?: Blob;
        label: string;
        batch?: PointBatch;
        annotations?: readonly AnnotationView[];
        annotationClasses?: readonly AnnotationClassColor[];
        projection?: CameraProjectionView;
        onEnlarge?: () => void;
        projectionSettings?: ProjectionSettings;
        /** `row`: the strip's height sizes the tile; `column`: the strip's width does. */
        layout?: 'row' | 'column';
    }
    let {
        datasetId,
        recordingId,
        channelId,
        keyframeTimestampNs,
        logTimeNs,
        blob,
        label,
        batch,
        annotations = [],
        annotationClasses = [],
        projection,
        onEnlarge,
        projectionSettings,
        layout = 'row'
    }: Props = $props();

    const frame = useCameraFrame(() => ({
        datasetId,
        recordingId,
        channelId,
        keyframeTimestampNs,
        logTimeNs,
        blob,
        label
    }));
</script>

<figure
    class="flex shrink-0 flex-col overflow-hidden bg-muted/30 {layout === 'column'
        ? 'w-full min-w-0'
        : 'h-full'}"
    style:width={layout === 'row' ? `${frame.tileWidth}px` : undefined}
    style:height={layout === 'column' ? `${frame.tileHeight}px` : undefined}
    bind:clientHeight={frame.figureHeight}
    bind:clientWidth={frame.figureWidth}
>
    {#if frame.frameUrl && frame.frameUrl !== frame.failedFrameUrl}
        <button
            type="button"
            class="flex min-h-0 w-full min-w-0 flex-1 cursor-zoom-in flex-col"
            aria-label={`Enlarge ${label}`}
            onclick={onEnlarge}
        >
            <div class="relative min-h-0 w-full flex-1">
                <img
                    src={frame.frameUrl}
                    alt={label}
                    class="h-full w-full object-contain"
                    onload={frame.handleLoad}
                    onerror={frame.handleError}
                />
                <ProjectionOverlay
                    {batch}
                    {annotations}
                    {annotationClasses}
                    {projection}
                    settings={projectionSettings}
                />
            </div>
        </button>
    {:else}
        <div class="flex min-h-0 flex-1 items-center justify-center text-muted-foreground">
            <Camera class="size-5" aria-hidden="true" />
        </div>
    {/if}
    <figcaption
        class="h-6 shrink-0 truncate px-2 text-center text-xs leading-6 text-muted-foreground"
    >
        {label}
    </figcaption>
</figure>
