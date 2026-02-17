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
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { toast } from 'svelte-sonner';
    import { useVideo } from '$lib/hooks/useVideo/useVideo';
    import { onMount } from 'svelte';
    import { getFrameBatchCursor } from '$lib/utils/frame';

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

    // Route validations in +layout.ts ensure these params are always present and valid
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = page.params.collection_id;

    const { removeTagFromSample } = useRemoveTagFromSample({ collectionId });
    const { collection: datasetCollection, refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({
            collectionId: datasetId
        })
    );
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
        await removeTagFromSample(videoData.sample_id, tagId);
        refetchVideo();
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
            // If this is the first caption, refresh root collection to update navigation
            if (!captions.length) {
                refetchRootCollection();
            }
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
    // This flag is used to prevent the onUpdate callback from changing the current frame while we are seeking to a specific frame number on load
    let seekFrameNumber = false;
    const BATCH_SIZE = 25;

    let resizeObserver: ResizeObserver;

    const frameNumber = $derived.by(() => {
        const frameNumberParam = page.url.searchParams.get('frame_number');
        return frameNumberParam ? parseInt(frameNumberParam) : null;
    });

    onMount(() => {
        loadFramesFromFrameNumber();
    });

    async function loadFramesFromFrameNumber() {
        if (frameNumber && videoEl) {
            seekFrameNumber = true;
            cursor = getFrameBatchCursor(frameNumber, BATCH_SIZE);

            await loadFrames();

            currentFrame = frames.find((frame) => frame.frame_number === frameNumber) ?? null;

            if (currentFrame) videoEl!.currentTime = currentFrame.frame_timestamp_s + 0.002;
        }

        hasStarted = true;
    }

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
        if (!hasStarted || seekFrameNumber) return;

        currentFrame = frame;

        if (index != null && index % BATCH_SIZE == 0 && index != 0 && currentIndex < index) {
            loadFrames();
        }
    }

    async function loadFrames() {
        if (loading || reachedEnd) return;
        loading = true;

        const frameCollectionId = (videoData?.frame?.sample as SampleView)?.collection_id;
        if (!frameCollectionId) return;

        const res = await getAllFrames({
            path: {
                video_frame_collection_id: frameCollectionId
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

        frames = mergeFrames(frames, newFrames);

        cursor = res?.data?.nextCursor ?? cursor + BATCH_SIZE;

        loading = false;
    }

    function onPlay() {
        loadFrames();
    }

    function goToNextVideo() {
        if (videoIndex === null || !videoData) return null;
        if (!videoAdjacents) return null;

        const sampleNext = $videoAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toVideosDetails(
                datasetId,
                collectionType,
                collectionId,
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
                datasetId,
                collectionType,
                collectionId,
                samplePrevious.sample_id,
                videoIndex - 1
            )
        );
    }

    let lastVideoId: string | null = null;

    $effect(() => {
        if (!videoData) return;

        const videoId = videoData.sample_id;

        if (videoId !== lastVideoId && hasStarted) {
            frames = videoData.frame ? [videoData.frame] : [];
            currentFrame = videoData.frame ?? null;
            cursor = 0;
            currentIndex = 0;
            loading = false;
            reachedEnd = false;

            lastVideoId = videoId;
        }
    });

    function handleKeyDownEvent(event: KeyboardEvent) {
        // Ignore when typing in inputs / textareas
        const target = event.target as HTMLElement;
        if (target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA') return;

        if (event.code === 'Space') {
            event.preventDefault(); // prevent page scroll

            if (!videoEl) return;

            if (videoEl.paused) {
                videoEl.play();
            } else {
                videoEl.pause();
            }
        }
    }

    async function onSeeked(event: Event) {
        if (seekFrameNumber) seekFrameNumber = false;

        const target = event.target as HTMLVideoElement;

        if (!videoData) return;

        // Estimate the frame index based on current time and video FPS
        const frameIndex = Math.floor(target.currentTime * videoData.fps);

        // Estimate the cursor position for fetching frames around the current frame index
        cursor = getFrameBatchCursor(frameIndex, BATCH_SIZE);

        await loadFrames();

        // Find the exact frame
        currentFrame = frames.find((frame) => frame.frame_number === frameIndex) ?? null;
    }

    function mergeFrames(existingFrames: FrameView[], newFrames: FrameView[]): FrameView[] {
        if (existingFrames.at(-1)?.frame_number === newFrames[0]?.frame_number) {
            // If the last existing frame is the same as the first new frame, we can just concatenate
            return [...existingFrames, ...newFrames];
        }

        const frameMap = new Map<string, FrameView>();

        existingFrames.forEach((frame) => frameMap.set(frame.sample_id, frame));
        newFrames.forEach((frame) => frameMap.set(frame.sample_id, frame));

        return Array.from(frameMap.values()).sort((a, b) => a.frame_number - b.frame_number);
    }
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center">
        {#if $datasetCollection.data && !Array.isArray($datasetCollection.data)}
            <DetailsBreadcrumb
                rootCollection={$datasetCollection.data}
                section="Videos"
                subsection="Video"
                navigateTo={(collectionId) =>
                    datasetId && collectionType
                        ? routeHelpers.toVideos(datasetId, collectionType, collectionId)
                        : '#'}
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
                                onseeked={onSeeked}
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
                    <div class="min-w-full space-y-3 text-diffuse-foreground">
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="File Name"
                                >File Name:</span
                            >
                            <span class="text-sm" data-testid="video-file-name"
                                >{videoData?.file_name}</span
                            >
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Width">Width:</span>
                            <span class="text-sm" data-testid="video-width"
                                >{videoData?.width}px</span
                            >
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Height">Height:</span>
                            <span class="text-sm" data-testid="video-height"
                                >{videoData?.height}px</span
                            >
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
                            {#each captions as caption (caption.sample_id)}
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
                                    class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
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
                        <div class="space-y-2 text-sm text-diffuse-foreground">
                            <div class="flex items-center gap-2">
                                <span class="font-medium">Frame #:</span>
                                <span data-testid="current-frame-number"
                                    >{currentFrame.frame_number}</span
                                >
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">Timestamp:</span>
                                <span data-testid="current-frame-timestamp"
                                    >{currentFrame.frame_timestamp_s.toFixed(3)} s</span
                                >
                            </div>
                        </div>

                        <Button
                            variant="secondary"
                            class="mt-4 w-full"
                            href={(() => {
                                const frameCollectionId = (currentFrame.sample as SampleView)
                                    .collection_id;
                                if (!frameCollectionId) return '#';
                                return routeHelpers.toFramesDetails(
                                    datasetId,
                                    'video_frame',
                                    frameCollectionId,
                                    currentFrame.sample_id
                                );
                            })()}
                            data-testid="view-frame-button"
                        >
                            View frame
                        </Button>
                    {/if}
                </Segment>
            </CardContent>
        </Card>
    </div>
</div>

<svelte:window onkeydown={handleKeyDownEvent} />

<style>
    .video-frame-container {
        width: 100%;
        height: 100%;
    }
</style>
