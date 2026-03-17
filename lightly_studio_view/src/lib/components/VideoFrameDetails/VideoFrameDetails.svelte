<script lang="ts">
    import { type FrameView, type SampleView, type VideoView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { Button } from '$lib/components/ui';
    import { routeHelpers } from '$lib/routes';
    import { useVideoFrames } from '$lib/hooks/useVideoFrames/useVideoFrames';
    import { onMount } from 'svelte';

    interface VideoFrameDetailsProps {
        videoData: VideoView;
        datasetId: string;
        frameNumber?: number;
        playbackTime?: number;
    }

    let {
        videoData,
        datasetId,
        frameNumber = $bindable(),
        playbackTime = $bindable(0)
    }: VideoFrameDetailsProps = $props();

    let { currentFrame, playbackTime: hookPlaybackTime, loadFrameByPlaybackTime, loadFramesFromFrameNumber } = useVideoFrames({
        videoData
    });

    onMount(async () => {
        if (playbackTime && videoData.fps) {
            await loadFrameByPlaybackTime(playbackTime, videoData.fps).catch((error) => {
                console.error('Failed to load frame by playback time:', error);
            });
        } else if (frameNumber !== undefined && frameNumber !== null) {
            await loadFramesFromFrameNumber(frameNumber);
        }
    });

    // Sync bindable playbackTime with hook's playbackTime store
    $effect(() => {
        playbackTime = $hookPlaybackTime;
    });

    // Sync bindable frameNumber with currentFrame's frame_number
    $effect(() => {
        if ($currentFrame) {
            frameNumber = $currentFrame.frame_number;
        }
    });

    // Load frame when playbackTime changes
    $effect(() => {
        if (playbackTime !== undefined && videoData.fps !== undefined) {
            loadFrameByPlaybackTime(playbackTime, videoData.fps).catch((error) => {
                console.error('Failed to load frame by playback time:', error);
            });
        }
    });

    function getFrameDetailsRoute(frame: FrameView): string {
        const frameCollectionId = (frame.sample as SampleView).collection_id;
        if (!frameCollectionId) return '#';
        return routeHelpers.toFramesDetails(
            datasetId,
            'video_frame',
            frameCollectionId,
            frame.sample_id,
            true
        );
    }
</script>

{#if $currentFrame}
    <Segment title="Current Frame">
        <div class="space-y-2 text-sm text-diffuse-foreground">
            <div class="flex items-center gap-2">
                <span class="font-medium">Frame #:</span>
                <span data-testid="current-frame-number">{$currentFrame.frame_number}</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="font-medium">Timestamp:</span>
                <span data-testid="current-frame-timestamp"
                    >{$currentFrame.frame_timestamp_s.toFixed(3)} s</span
                >
            </div>
        </div>

        <Button
            variant="secondary"
            class="mt-4 w-full"
            href={getFrameDetailsRoute($currentFrame)}
            data-testid="view-frame-button"
        >
            View frame
        </Button>
    </Segment>
{/if}
