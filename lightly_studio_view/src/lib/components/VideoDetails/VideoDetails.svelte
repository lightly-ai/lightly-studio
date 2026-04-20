<script lang="ts">
    import {
        CanvasVideoPlayer,
        Card,
        CardContent,
        MetadataSegment,
        SegmentTags,
        VideoDetailsNavigation,
        VideoFrameDetails
    } from '$lib/components';
    import { type SampleView, type VideoView } from '$lib/api/lightly_studio_local';
    import { getVideoURLById } from '$lib/utils';
    import VideoSampleMetadata from '../VideoSampleMetadata/VideoSampleMetadata.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetails/SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
    import { onMount } from 'svelte';
    import { routeHelpers } from '$lib/routes';

    type VideoDetailsProps = {
        video: VideoView;
        datasetId: string;
        onVideoUpdate: () => void;
        frameNumber?: number;
    };
    const { video, datasetId, onVideoUpdate, frameNumber }: VideoDetailsProps = $props();

    const {
        currentFrame,
        frames: videoFrames,
        setCurrentFrame,
        loadFramesFromFrameNumber
    } = useVideoFrames({
        video
    });

    onMount(() => {
        if (frameNumber != null) {
            void loadFramesFromFrameNumber(frameNumber);
        } else {
            void loadFramesFromFrameNumber(0);
        }
    });
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex w-[60vw] flex-col">
            <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
                <div class="video-frame-container relative overflow-hidden rounded-lg bg-black">
                    <VideoDetailsNavigation />
                    <CanvasVideoPlayer
                        src={getVideoURLById(video.sample_id)}
                        frames={$videoFrames}
                        sampleWidth={video.width}
                        sampleHeight={video.height}
                        showControls={true}
                        initialFrameNumber={frameNumber}
                        className="block h-full w-full"
                        onFrameChange={setCurrentFrame}
                    />
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
