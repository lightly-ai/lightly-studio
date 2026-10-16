<script lang="ts">
    import { Camera } from '@lucide/svelte';
    import * as Dialog from '$lib/components/ui/dialog';
    import { getCameraFrameUrl } from '../getCameraFrameUrl/getCameraFrameUrl';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';

    /**
     * A single camera tile in the projection strip. Renders the channel's frame
     * for the active tick, falling back to a placeholder camera icon when the
     * image fails to load. Clicking the frame enlarges it in a dialog over the
     * workspace; the enlarged frame follows the active tick.
     */
    interface Props {
        /** Dataset the recording belongs to. */
        datasetId: string;
        /** Recording that owns the frame. */
        recordingId?: string;
        /** MCAP channel to render. */
        channelId: number;
        /** Keyframe to decode from, in nanoseconds, as a string to preserve full precision. */
        keyframeTimestampNs?: string;
        /** Frame to show, in nanoseconds, as a string to preserve full precision. */
        logTimeNs?: string;
        /** Studio slot name shown as the caption, e.g. `front`. */
        label: string;
        batch?: PointBatch;
        annotations?: readonly AnnotationView[];
        projection?: CameraProjectionView;
    }

    let {
        datasetId,
        recordingId,
        channelId,
        keyframeTimestampNs,
        logTimeNs,
        label,
        batch,
        annotations = [],
        projection
    }: Props = $props();

    const frameUrl = $derived(
        recordingId && keyframeTimestampNs && logTimeNs
            ? getCameraFrameUrl({
                  datasetId,
                  recordingId,
                  channelId,
                  keyframeTimestampNs,
                  logTimeNs
              })
            : null
    );

    let failedFrameUrl = $state<string | null>(null);
    let isEnlarged = $state(false);
    // Tile width follows the frame's own aspect ratio; square until the image has loaded.
    let aspectRatio = $state(1);
    let figureHeight = $state(0);
    const CAPTION_HEIGHT_PX = 24;
    const BORDER_PX = 2;
    const tileWidth = $derived(
        Math.max(0, figureHeight - CAPTION_HEIGHT_PX) * aspectRatio + BORDER_PX
    );
</script>

<figure
    class="flex h-full shrink-0 flex-col overflow-hidden rounded-md border bg-muted/30"
    style:width={`${tileWidth}px`}
    bind:clientHeight={figureHeight}
>
    {#if frameUrl && frameUrl !== failedFrameUrl}
        <button
            type="button"
            class="flex min-h-0 flex-1 cursor-zoom-in flex-col"
            aria-label={`Enlarge ${label}`}
            onclick={() => (isEnlarged = true)}
        >
            <div class="relative min-h-0 flex-1">
                <img
                    src={frameUrl}
                    alt={label}
                    class="h-full w-full object-contain"
                    onload={(event) => {
                        const { naturalWidth, naturalHeight } =
                            event.currentTarget as HTMLImageElement;
                        if (naturalWidth && naturalHeight)
                            aspectRatio = naturalWidth / naturalHeight;
                    }}
                    onerror={() => (failedFrameUrl = frameUrl)}
                />
                <ProjectionOverlay {batch} {annotations} {projection} />
            </div>
        </button>
        <Dialog.Root bind:open={isEnlarged}>
            <Dialog.Content class="max-w-[90vw] gap-2 p-3 sm:max-w-[90vw]">
                <Dialog.Title class="text-sm font-medium">{label}</Dialog.Title>
                <Dialog.Description class="sr-only">Enlarged camera frame</Dialog.Description>
                <div class="relative">
                    <img
                        src={frameUrl}
                        alt={`${label} enlarged`}
                        class="max-h-[80vh] w-full rounded-md object-contain"
                    />
                    <ProjectionOverlay {batch} {annotations} {projection} />
                </div>
            </Dialog.Content>
        </Dialog.Root>
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
