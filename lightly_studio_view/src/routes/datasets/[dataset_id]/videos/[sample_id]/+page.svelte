<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';
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
    import type { Writable } from 'svelte/store';
    import type { VideoAdjacents } from '$lib/hooks/useVideoAdjacents/useVideoAdjancents';
    import { goto } from '$app/navigation';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import DetailsBreadcrumb from '$lib/components/DetailsBreadcrumb/DetailsBreadcrumb.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import MetadataSegment from '$lib/components/MetadataSegment/MetadataSegment.svelte';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { useRootDatasetOptions } from '$lib/hooks/useRootDataset/useRootDataset';
    import { page } from '$app/state';
    import { invalidateAll } from '$app/navigation';

    const { data }: { data: PageData } = $props();
    const {
        sample,
        videoIndex,
        videoAdjacents
    }: {
        sample: VideoView | undefined;
        videoIndex: number | null;
        videoAdjacents: Writable<VideoAdjacents> | null;
    } = $derived(data);

    const { datasetId } = page.data;
    const { removeTagFromSample } = useRemoveTagFromSample({ datasetId });
    const { rootDataset } = useRootDatasetOptions({ datasetId });

    const tags = $derived(
        ((sample?.sample as SampleView)?.tags as Array<{ tag_id: string; name: string }>)?.map(
            (t) => ({
                tagId: t.tag_id,
                name: t.name
            })
        ) ?? []
    );

    const handleRemoveTag = async (tagId: string) => {
        if (!sample?.sample_id) return;
        try {
            await removeTagFromSample(sample.sample_id, tagId);
            // Refresh the page data to get updated tags
            await invalidateAll();
        } catch (error) {
            console.error('Error removing tag from video:', error);
        }
    };

    let videoEl: HTMLVideoElement | null = $state(null);
    let frames = $state<FrameView[]>([]);

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

    function goToNextVideo() {
        if (videoIndex === null || !sample) return null;
        if (!videoAdjacents) return null;

        const sampleNext = $videoAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toVideosDetails(
                (sample.sample as SampleView).dataset_id,
                sampleNext.sample_id,
                videoIndex + 1
            )
        );
    }

    function goToPreviousVideo() {
        if (videoIndex === null || !sample) return null;
        if (!videoAdjacents) return null;

        const samplePrevious = $videoAdjacents?.samplePrevious;
        if (!samplePrevious) return null;

        goto(
            routeHelpers.toVideosDetails(
                (sample.sample as SampleView).dataset_id,
                samplePrevious.sample_id,
                videoIndex - 1
            )
        );
    }

    let lastVideoId: string | null = null;

    $effect(() => {
        if (!sample) return;

        const videoId = sample.sample_id;

        if (videoId !== lastVideoId) {
            frames = sample.frame ? [sample.frame] : [];
            currentFrame = sample.frame ?? null;
            cursor = 0;
            currentIndex = 0;
            loading = false;
            reachedEnd = false;

            lastVideoId = videoId;
        }
    });
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center">
        {#if $rootDataset.data}
            <DetailsBreadcrumb
                rootDataset={$rootDataset.data}
                section="Videos"
                subsection="Video"
                navigateTo={routeHelpers.toVideos}
                index={videoIndex}
            />
        {/if}
    </div>
    <Separator class="mb-4 bg-border-hard" />
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex w-[60vw] flex-col">
            <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
                <div
                    bind:this={containerEl}
                    class="video-frame-container relative overflow-hidden rounded-lg bg-black"
                >
                    {#if $videoAdjacents}
                        <SteppingNavigation
                            hasPrevious={!!$videoAdjacents?.samplePrevious}
                            hasNext={!!$videoAdjacents?.sampleNext}
                            onPrevious={goToPreviousVideo}
                            onNext={goToNextVideo}
                        />
                    {/if}
                    {#key sample?.sample_id}
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
                    {/key}
                </div>
            </CardContent>
        </Card>

        <Card className="flex flex-1 flex-col overflow-hidden">
            <CardContent className="h-full overflow-y-auto">
                <SegmentTags {tags} onClick={handleRemoveTag} />
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
                            <span class="truncate text-sm font-medium" title="Duration"
                                >Duration:</span
                            >
                            <span class="text-sm">{sample?.duration_s?.toFixed(2)} seconds</span>
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
                            <span class="text-sm">{sample?.fps.toFixed(2)}</span>
                        </div>
                    </div>
                </Segment>
                <MetadataSegment metadata_dict={(sample?.sample as SampleView).metadata_dict} />
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
                                (currentFrame.sample as SampleView).dataset_id,
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
</div>

<style>
    .video-frame-container {
        width: 100%;
        height: 100%;
    }
</style>
