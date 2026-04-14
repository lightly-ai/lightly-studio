<script lang="ts">
    import {
        Card,
        CardContent,
        MetadataSegment,
        SegmentTags,
        Spinner,
        VideoDetailsNavigation
    } from '$lib/components';
    import { type SampleView, type VideoView } from '$lib/api/lightly_studio_local';
    import { getVideoURLById } from '$lib/utils';
    import VideoSampleMetadata from '../VideoSampleMetadata/VideoSampleMetadata.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetails/SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
    import { get } from 'svelte/store';
    import { onMount } from 'svelte';
    import CanvasVideoPlayer, {
        type SelectionModeOverride
    } from '$lib/components/CanvasVideoPlayer/CanvasVideoPlayer.svelte';

    type VideoDetailsProps = {
        video: VideoView;
        datasetId: string;
        onVideoUpdate: () => void;
        frameNumber?: number;
    };
    const { video, datasetId, onVideoUpdate, frameNumber }: VideoDetailsProps = $props();

    let playerReady = $state(false);
    let initialFrameIndex = $state(0);
    let selectionModeOverride = $state<SelectionModeOverride>('hybrid');
    const { frames: videoFrames, loadFrames } = useVideoFrames({ video });

    onMount(() => {
        void (async () => {
            await loadFrames();
            const frames = get(videoFrames);

            if (frameNumber !== undefined) {
                initialFrameIndex = Math.max(
                    0,
                    frames.findIndex((frame) => frame.frame_number === frameNumber)
                );
            }

            playerReady = true;
        })();
    });
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex w-[60vw] flex-col">
            <CardContent className="flex h-full flex-col gap-4 overflow-hidden">
                <VideoDetailsNavigation />
                {#if playerReady}
                    <CanvasVideoPlayer
                        src={getVideoURLById(video.sample_id)}
                        frames={$videoFrames}
                        sampleWidth={video.width}
                        sampleHeight={video.height}
                        {initialFrameIndex}
                        className="min-h-0 flex-1"
                        {selectionModeOverride}
                        showDebug={true}
                        showSelectionModeDebugControls={true}
                    />
                {:else}
                    <div
                        class="video-frame-container flex min-h-0 flex-1 items-center justify-center rounded-lg bg-black"
                    >
                        <Spinner />
                    </div>
                {/if}
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
