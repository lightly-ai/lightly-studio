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
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import { page } from '$app/state';
    import { invalidateAll } from '$app/navigation';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { toast } from 'svelte-sonner';
    import { useVideo } from '$lib/hooks/useVideo/useVideo';

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

    const { collectionId } = page.data;
    const { removeTagFromSample } = useRemoveTagFromSample({ collectionId });
    const { rootCollection } = useRootCollectionOptions({ collectionId });
    const { deleteCaption } = useDeleteCaption();
    const { createCaption } = useCreateCaption();
    const { isEditingMode } = page.data.globalStorage;

    // Use client-side query hook for video data
    const { video: videoQuery, refetch: refetchVideo } = $derived(
        useVideo({ sampleId: sample?.sample_id ?? '' })
    );
    const videoData = $derived($videoQuery.data ?? sample);

    const tags = $derived(
        ((videoData?.sample as SampleView)?.tags as Array<{ tag_id: string; name: string }>)?.map(
            (t) => ({
                tagId: t.tag_id,
                name: t.name
            })
        ) ?? []
    );

    const handleRemoveTag = async (tagId: string) => {
        if (!videoData?.sample_id) return;
        try {
            await removeTagFromSample(videoData.sample_id, tagId);
            // Refresh the video data
            refetchVideo();
        } catch (error) {
            console.error('Error removing tag from video:', error);
        }
    };

    // Use videoData from query
    const captions = $derived((videoData?.sample as SampleView)?.captions ?? []);

    const handleDeleteCaption = async (sampleId: string) => {
        if (!videoData?.sample_id) return;
        try {
            await deleteCaption(sampleId);
            toast.success('Caption deleted successfully');
            refetchVideo();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const handleCreateCaption = async (sampleId: string) => {
        if (!videoData?.sample_id) return;
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            refetchVideo();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };

    const onCaptionUpdate = () => {
        refetchVideo();
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
                video_frame_collection_id: (videoData?.frame?.sample as SampleView).collection_id
            },
            query: {
                cursor,
                limit: BATCH_SIZE
            },
            body: {
                filter: {
                    video_id: videoData?.sample_id
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
        if (videoIndex === null || !videoData) return null;
        if (!videoAdjacents) return null;

        const sampleNext = $videoAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toVideosDetails(
                (videoData.sample as SampleView).collection_id,
                sampleNext.sample_id,
                videoIndex + 1
            )
        );
    }

    function goToPreviousVideo() {
        if (videoIndex === null || !videoData) return null;
        if (!videoAdjacents) return null;

        const samplePrevious = $videoAdjacents?.samplePrevious;
        if (!samplePrevious) return null;

        goto(
            routeHelpers.toVideosDetails(
                (videoData.sample as SampleView).collection_id,
                samplePrevious.sample_id,
                videoIndex - 1
            )
        );
    }

    let lastVideoId: string | null = null;

    $effect(() => {
        if (!videoData) return;

        const videoId = videoData.sample_id;

        if (videoId !== lastVideoId) {
            frames = videoData.frame ? [videoData.frame] : [];
            currentFrame = videoData.frame ?? null;
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
        {#if $rootCollection.data}
            <DetailsBreadcrumb
                rootCollection={$rootCollection.data}
                section="Videos"
                subsection="Video"
                navigateTo={routeHelpers.toVideos}
                index={videoIndex}
            />
        {/if}
    </div>
    <Separator class="bg-border-hard mb-4" />
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
                    {#key videoData?.sample_id}
                        {#if videoData}
                            <Video
                                bind:videoEl
                                video={videoData}
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
                                    sampleWidth={videoData.width}
                                    sampleHeight={videoData.height}
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
                    <div class="text-diffuse-foreground min-w-full space-y-3">
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Width">Width:</span>
                            <span class="text-sm">{videoData?.width}px</span>
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Height">Height:</span>
                            <span class="text-sm">{videoData?.height}px</span>
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Duration"
                                >Duration:</span
                            >
                            <span class="text-sm">{videoData?.duration_s?.toFixed(2)} seconds</span>
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
                            <span class="text-sm">{videoData?.fps.toFixed(2)}</span>
                        </div>
                    </div>
                </Segment>
                <MetadataSegment metadata_dict={(videoData?.sample as SampleView).metadata_dict} />
                <Segment title="Captions">
                    <div class="flex flex-col gap-3 space-y-4">
                        <div class="flex flex-col gap-2">
                            {#each captions as caption}
                                <CaptionField
                                    {caption}
                                    onDeleteCaption={() => handleDeleteCaption(caption.sample_id)}
                                    onUpdate={onCaptionUpdate}
                                />
                            {/each}
                            <!-- Add new caption button -->
                            {#if $isEditingMode}
                                <button
                                    type="button"
                                    class="bg-card text-diffuse-foreground hover:bg-primary hover:text-primary-foreground mb-2 flex h-8 items-center justify-center rounded-sm px-2 py-0 transition-colors"
                                    onclick={() => handleCreateCaption(videoData?.sample_id ?? '')}
                                    data-testid="add-caption-button"
                                >
                                    +
                                </button>
                            {/if}
                        </div>
                    </div>
                </Segment>
                <Segment title="Current Frame">
                    {#if currentFrame}
                        <div class="text-diffuse-foreground space-y-2 text-sm">
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
                                (currentFrame.sample as SampleView).collection_id,
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
