<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import { type FrameView, type VideoView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '$lib/components/VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: VideoView } = $derived(data);

    let videoEl: HTMLVideoElement | null = null;
    let currentFrame: FrameView | null = $state(onTimeUpdate());

    let containerEl: HTMLDivElement | null = null;
    let overlaySize = $state(0);
    let overlayHeight = $state(0);

    $effect(() => {
        if (containerEl) {
            overlaySize = containerEl.clientWidth;
            overlayHeight = containerEl.clientHeight;
        }
    });

    function onTimeUpdate(): FrameView | null {
        if (!sample.frames || sample.frames.length === 0 || !videoEl) return null;

        const currentTime = videoEl.currentTime;
        const pastFrames = sample.frames.filter((f) => f.frame_timestamp_s <= currentTime);

        const frame =
            pastFrames.length > 0
                ? pastFrames.reduce((prev, curr) =>
                      curr.frame_timestamp_s > prev.frame_timestamp_s ? curr : prev
                  )
                : sample.frames[0];

        currentFrame = frame;
        return frame;
    }
</script>

<div class="flex h-full w-full flex-row gap-4 overflow-hidden p-4">
    <Card className="flex w-[60vw] flex-col">
        <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
            <div
                bind:this={containerEl}
                class="video-frame-container relative overflow-hidden rounded-lg bg-black"
            >
                <video
                    src={`${PUBLIC_VIDEOS_MEDIA_URL}/${sample.sample_id}`}
                    muted
                    controls
                    bind:this={videoEl}
                    ontimeupdate={onTimeUpdate}
                    class="block h-full w-full"
                ></video>

                {#if currentFrame && overlaySize > 0}
                    <VideoFrameAnnotationItem
                        width={overlaySize}
                        height={overlayHeight}
                        sample={currentFrame}
                        showLabel={true}
                        sampleWidth={sample.width}
                        sampleHeight={sample.height}
                    />
                {/if}
            </div>
        </CardContent>
    </Card>

    <Card className="flex flex-1 flex-col overflow-hidden">
        <CardContent className="h-full overflow-y-auto">
            <Segment title="Sample details">
                <div class="min-w-full space-y-3 text-diffuse-foreground">
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Width">Width:</span>
                        <span class="text-sm">{sample.width}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Height">Height:</span>
                        <span class="text-sm">{sample.height}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Duration">Duration:</span>
                        <span class="text-sm">{sample.duration_s.toFixed(2)} seconds</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
                        <span class="text-sm">{sample.fps.toFixed(2)}</span>
                    </div>
                </div>
            </Segment>

            <Segment title="Current Frame">
                {#if currentFrame}
                    <div class="space-y-2 text-sm text-diffuse-foreground">
                        <div class="flex items-center gap-2">
                            <span class="font-medium">Frame #:</span>
                            <span>{currentFrame.frame_number}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="font-medium">Timestamp:</span>
                            <span>{currentFrame.frame_timestamp_s.toFixed(3)} s</span>
                        </div>
                    </div>

                    <Button
                        variant="secondary"
                        class="mt-4 w-full"
                        href={routeHelpers.toFramesDetails(
                            currentFrame.sample.dataset_id,
                            currentFrame.sample_id
                        )}
                    >
                        View frame
                    </Button>
                {/if}
            </Segment>
        </CardContent>
    </Card>
</div>

<style>
    .video-frame-container {
        width: 100%;
        height: 100%;
    }

    video {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }
</style>
