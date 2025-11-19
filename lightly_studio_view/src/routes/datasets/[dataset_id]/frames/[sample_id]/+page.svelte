<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from '../[sampleId]/$types';
    import type { SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';
    import ZoomableContainer from '$lib/components/ZoomableContainer/ZoomableContainer.svelte';
    import type { Writable } from 'svelte/store';
    import type { FrameAdjacents } from '$lib/hooks/useFramesAdjacents/useFramesAdjacents';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import FrameDetailsBreadcrumb from '$lib/components/FrameDetailsBreadcrumb/FrameDetailsBreadcrumb.svelte';
    import { Separator } from '$lib/components/ui/separator';

    const { data }: { data: PageData } = $props();
    const {
        sample,
        frameIndex,
        frameAdjacents
    }: {
        sample: VideoFrameView;
        frameIndex: number | null;
        frameAdjacents: Writable<FrameAdjacents> | null;
    } = $derived(data);

    function goToNextFrame() {
        if (frameIndex == null) return null;
        if (!frameAdjacents) return null;

        const sampleNext = $frameAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toFramesDetails(
                (sample.sample as SampleView).dataset_id,
                sampleNext.sample_id,
                frameIndex + 1
            )
        );
    }

    function goToPreviousFrame() {
        if (frameIndex == null) return null;
        if (!frameAdjacents) return null;

        const samplePrevious = $frameAdjacents?.samplePrevious;
        if (!samplePrevious) return null;

        goto(
            routeHelpers.toFramesDetails(
                (sample.sample as SampleView).dataset_id,
                samplePrevious.sample_id,
                frameIndex - 1
            )
        );
    }
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center">
        <FrameDetailsBreadcrumb dataset={data.dataset} {frameIndex} />
    </div>
    <Separator class="mb-4 bg-border-hard" />
    <div class="flex min-h-0 flex-1 gap-4">
        <Card className="flex flex-col w-[60vw]">
            <CardContent className="flex flex-col gap-4 overflow-hidden h-full">
                <div class="relative h-full w-full overflow-hidden">
                    {#if frameAdjacents}
                        <SteppingNavigation
                            hasPrevious={!!$frameAdjacents?.samplePrevious}
                            hasNext={!!$frameAdjacents?.sampleNext}
                            onPrevious={goToPreviousFrame}
                            onNext={goToNextFrame}
                        />
                    {/if}
                    <ZoomableContainer width={sample.video.width} height={sample.video.height}>
                        {#snippet zoomableContent()}
                            <image href={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}`} />
                        {/snippet}
                    </ZoomableContainer>
                </div>
            </CardContent>
        </Card>

        <Card className="flex flex-col flex-1 overflow-hidden">
            <CardContent className="h-full overflow-y-auto">
                <Segment title="Video frame details">
                    <div class="min-w-full space-y-3 text-diffuse-foreground">
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Width">Number:</span>
                            <span class="text-sm">{sample.frame_number}</span>
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="truncate text-sm font-medium" title="Height"
                                >Timestamp:</span
                            >
                            <span class="text-sm"
                                >{sample.frame_timestamp_s.toFixed(2)} seconds</span
                            >
                        </div>
                        <div class="flex items-start gap-3">
                            <span class="text-sm font-medium" title="Height">Video file path:</span>
                            <span class="w-auto break-all text-sm"
                                >{sample.video.file_path_abs}</span
                            >
                        </div>
                    </div>
                </Segment>
            </CardContent>
        </Card>
    </div>
</div>
