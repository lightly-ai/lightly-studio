<script lang="ts">
    import { Camera } from '@lucide/svelte';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';
    import CameraProjectionDialog from './CameraProjectionDialog.svelte';
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
        onPlaybackToggle?: () => void;
        projectionSettings?: ProjectionSettings;
        onProjectionSettingsChange?: (settings: ProjectionSettings) => void;
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
        onPlaybackToggle,
        projectionSettings,
        onProjectionSettingsChange
    }: Props = $props();

    let isEnlarged = $state(false);
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
    class="flex h-full shrink-0 flex-col overflow-hidden bg-muted/30"
    style:width={`${frame.tileWidth}px`}
    bind:clientHeight={frame.figureHeight}
>
    {#if frame.frameUrl && frame.frameUrl !== frame.failedFrameUrl}
        <button
            type="button"
            class="flex min-h-0 flex-1 cursor-zoom-in flex-col"
            aria-label={`Enlarge ${label}`}
            onclick={() => (isEnlarged = true)}
        >
            <div class="relative min-h-0 flex-1">
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
        <CameraProjectionDialog
            bind:open={isEnlarged}
            {label}
            imageUrl={frame.fullFrameUrl ?? frame.frameUrl}
            {batch}
            {annotations}
            {annotationClasses}
            {projection}
            {projectionSettings}
            {onProjectionSettingsChange}
            {onPlaybackToggle}
        />
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
