<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import type { PageData } from './$types';
    import {
        getAllFrames,
        type FrameView,
        type SampleView,
        type VideoFrameView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '$lib/components/VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import Video from '$lib/components/Video/Video.svelte';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: VideoView | undefined } = $derived(data);

    let videoEl: HTMLVideoElement | null = $state(null);
    let frames = $state<FrameView[]>(data.sample?.frame == null ? [] : [data.sample.frame]);

    let currentFrame: FrameView | null | undefined = $state();

    let containerEl: HTMLDivElement | null = null;
    let overlaySize = $state(0);
    let overlayHeight = $state(0);
    let currentIndex = 0;
    let hasStarted = false;
    let cursor = 0;
    let loading = false;
    let reachedEnd = false;
    const BATCH_SIZE = 25;

    let resizeObserver: ResizeObserver;

    $effect(() => {
        if (!videoEl) return;

        const updateOverlaySize = () => {
            const rect = videoEl?.getBoundingClientRect();
            overlaySize = rect?.width ?? 0;
            overlayHeight = rect?.height ?? 0;
        };

        updateOverlaySize();

        resizeObserver = new ResizeObserver(updateOverlaySize);
        resizeObserver.observe(videoEl);

        return () => resizeObserver.disconnect();
    });

    function onUpdate(frame: FrameView | VideoFrameView | null, index: number | null) {
        currentFrame = frame;
        if (index != null && index % BATCH_SIZE == 0 && index != 0 && currentIndex < index) {
            loadFrames();
        }
    }

    async function loadFrames() {
        if (loading || reachedEnd) return;
        loading = true;

        const res = await getAllFrames({
            path: {
                video_frame_dataset_id: (sample?.frame?.sample as SampleView).dataset_id
            },
            query: {
                cursor,
                limit: BATCH_SIZE
            },
            body: {
                filter: {
                    video_id: sample?.sample_id
                }
            }
        });

        const newFrames = res?.data?.data ?? [];

        if (newFrames.length === 0) {
            reachedEnd = true;
            loading = false;
            return;
        }

        frames = [...frames, ...newFrames];

        cursor = res?.data?.nextCursor ?? cursor + BATCH_SIZE;

        loading = false;
    }

    function onPlay() {
        if (!hasStarted) loadFrames();
    }
</script>

<div class="flex h-full w-full flex-row gap-4 overflow-hidden p-4">
    <Card className="flex w-[60vw] flex-col">
        <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
            <div
                bind:this={containerEl}
                class="video-frame-container relative overflow-hidden rounded-lg bg-black"
            >
                {#if sample}
                    <Video
                        bind:videoEl
                        video={sample}
                        {frames}
                        muted={true}
                        controls={true}
                        update={onUpdate}
                        className="block h-full w-full"
                        onplay={onPlay}
                    />

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
                        <span class="text-sm">{sample?.width}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Height">Height:</span>
                        <span class="text-sm">{sample?.height}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Duration">Duration:</span>
                        <span class="text-sm">{sample?.duration_s?.toFixed(2)} seconds</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
                        <span class="text-sm">{sample?.fps.toFixed(2)}</span>
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
</style>
