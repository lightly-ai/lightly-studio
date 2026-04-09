<script lang="ts">
    import {
        Card,
        CardContent,
        MetadataSegment,
        SegmentTags,
        VideoDetailsNavigation,
        VideoFrameDetails,
        VideoPlayer
    } from '$lib/components';
    import { type FrameView, type SampleView, type VideoView } from '$lib/api/lightly_studio_local';
    import { getVideoURLById } from '$lib/utils';
    import VideoSampleMetadata from '../VideoSampleMetadata/VideoSampleMetadata.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetails/SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
    import { useVideoFrameAnnotations } from '$lib/hooks/useVideoFrameAnnotations/useVideoFrameAnnotations';
    import { onMount } from 'svelte';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem, {
        type PrerenderedAnnotation
    } from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';

    type VideoDetailsProps = {
        video: VideoView;
        datasetId: string;
        onVideoUpdate: () => void;
        frameNumber?: number;
    };
    const { video, datasetId, onVideoUpdate, frameNumber }: VideoDetailsProps = $props();

    let videoEl: HTMLVideoElement | null = $state(null);
    let frameRequestId: number | null = $state(null);

    const {
        currentFrame,
        frames: videoFrames,
        loadFrameByPlaybackTime,
        loadFramesFromFrameNumber
    } = useVideoFrames({
        video
    });

    $inspect($videoFrames, 'frames in VideoDetails');
    // Pre-render all frame annotations as dataURLs for efficient playback
    const frameAnnotationMap = $derived(
        useVideoFrameAnnotations({ frames: $videoFrames, imageWidth: video.width })
    );

    $inspect(frameAnnotationMap, 'frameAnnotationMap in VideoDetails');

    // Get prerendered annotations for current frame
    const prerenderedAnnotations = $derived.by((): PrerenderedAnnotation[] | undefined => {
        if (!$currentFrame) return undefined;
        return frameAnnotationMap.get($currentFrame.sample_id);
    });

    function stopFrameSyncLoop() {
        if (frameRequestId !== null) {
            cancelAnimationFrame(frameRequestId);
            frameRequestId = null;
        }
    }

    function startFrameSyncLoop() {
        stopFrameSyncLoop();

        const tick = () => {
            if (!videoEl) {
                frameRequestId = null;
                return;
            }

            void loadFrameByPlaybackTime(videoEl.currentTime, video.fps);
            frameRequestId = requestAnimationFrame(tick);
        };

        frameRequestId = requestAnimationFrame(tick);
    }

    const onplay = () => {
        startFrameSyncLoop();
    };

    const onpause = () => {
        stopFrameSyncLoop();
    };

    const onended = (event: Event) => {
        const target = event.target as HTMLVideoElement;
        void loadFrameByPlaybackTime(target.currentTime, video.fps);
        stopFrameSyncLoop();
    };

    const onseeked = (event: Event) => {
        const target = event.target as HTMLVideoElement;
        void loadFrameByPlaybackTime(target.currentTime, video.fps);
    };

    onMount(() => {
        if (frameNumber !== undefined) {
            void loadFramesFromFrameNumber(frameNumber);
            jumpToCurrentFrame = true;
        } else {
            void loadFrameByPlaybackTime(0, video.fps);
        }
    });

    $effect(() => {
        return () => stopFrameSyncLoop();
    });

    let videoWidth = $state(0);
    let videoHeight = $state(0);

    let resizeObserver: ResizeObserver;

    $effect(() => {
        if (!videoEl) return;

        const updateOverlaySize = () => {
            if (!videoEl) return;
            videoWidth = videoEl.clientWidth;
            videoHeight = videoEl.clientHeight;
        };
        updateOverlaySize();

        resizeObserver = new ResizeObserver(updateOverlaySize);
        resizeObserver.observe(videoEl);

        return () => resizeObserver.disconnect();
    });

    const getTimeByFrameNumber = (frame: FrameView) => {
        return frame.frame_timestamp_s + 0.002;
    };

    // this param is used when we passed frame_number to jump to specific frame on video load, after that we want to jump to current frame only when user seek or play the video
    let jumpToCurrentFrame: boolean = $state(false);

    // We track here if we have flag to jump to current frame
    $effect(() => {
        if (jumpToCurrentFrame && $currentFrame && videoEl) {
            const targetTime = getTimeByFrameNumber($currentFrame);
            videoEl.currentTime = targetTime;
            jumpToCurrentFrame = false;
        }
    });

    $inspect(prerenderedAnnotations, 'prerenderedAnnotations in VideoDetails');
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex w-[60vw] flex-col">
            <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
                <div class="video-frame-container relative overflow-hidden rounded-lg bg-black">
                    <VideoDetailsNavigation />
                    <VideoPlayer
                        src={getVideoURLById(video.sample_id)}
                        bind:videoEl
                        videoProps={{
                            controls: true,
                            muted: true,
                            class: 'block h-full w-full',
                            onplay,
                            onpause,
                            onended,
                            onseeked
                        }}
                    />

                    {#if $currentFrame && videoWidth > 0}
                        <VideoFrameAnnotationItem
                            width={videoWidth}
                            height={videoHeight}
                            sample={$currentFrame}
                            showLabel={true}
                            sampleWidth={video.width}
                            sampleHeight={video.height}
                            {prerenderedAnnotations}
                        />
                    {/if}
                </div>
            </CardContent>
        </Card>

        <Card className="flex flex-1 flex-col overflow-hidden">
            <CardContent className="h-full overflow-y-auto">
                {#if video?.sample?.sample_id}
                    <SegmentTags
                        tags={video.sample.tags ?? []}
                        collectionId={datasetId}
                        sampleId={video.sample.sample_id}
                        onRefetch={onVideoUpdate}
                    />
                {/if}
                <VideoSampleMetadata {video} />
                <MetadataSegment metadata_dict={(video?.sample as SampleView).metadata_dict} />
                {#if video?.sample?.sample_id}
                    <SampleDetailsCaptionSegment
                        refetch={onVideoUpdate}
                        captions={video?.sample?.captions ?? []}
                        sampleId={video?.sample?.sample_id}
                    />
                {/if}
                {#if $currentFrame}
                    {@const frameSample = $currentFrame.sample as SampleView}
                    {#if frameSample.collection_id && frameSample.sample_id}
                        {@const frameURL = routeHelpers.toFramesDetails(
                            datasetId,
                            'video_frame',
                            frameSample.collection_id,
                            frameSample.sample_id,
                            true
                        )}
                        <VideoFrameDetails frame={$currentFrame} {frameURL} />
                    {/if}
                {/if}
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
