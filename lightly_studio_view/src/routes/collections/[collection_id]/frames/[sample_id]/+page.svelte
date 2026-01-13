<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import { type SampleView, type VideoFrameView } from '$lib/api/lightly_studio_local';
    import { type Writable } from 'svelte/store';
    import type { FrameAdjacents } from '$lib/hooks/useFramesAdjacents/useFramesAdjacents';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import FrameDetailsBreadcrumb from '$lib/components/FrameDetailsBreadcrumb/FrameDetailsBreadcrumb.svelte';
    import { useFrame } from '$lib/hooks/useFrame/useFrame';
    import FrameDetailsSegment from '$lib/components/frames/FrameDetailsSegment/FrameDetailsSegment.svelte';
    import SampleDetailsPanel from '$lib/components/SampleDetails/SampleDetailsPanel.svelte';
    import MetadataSegment from '$lib/components/MetadataSegment/MetadataSegment.svelte';

    const { data }: { data: PageData } = $props();
    const {
        frameIndex,
        frameAdjacents,
        collectionId,
        sampleId
    }: {
        sample: VideoFrameView;
        frameIndex: number | null;
        frameAdjacents: Writable<FrameAdjacents> | null;
        collectionId: string;
        sampleId: string;
    } = $derived(data);
    const { refetch, videoFrame } = $derived(useFrame(sampleId));

    const sample = $derived($videoFrame.data);

    function goToNextFrame() {
        if (frameIndex == null || !sample) return null;
        if (!frameAdjacents) return null;

        const sampleNext = $frameAdjacents?.sampleNext;
        if (!sampleNext) return null;

        const collectionIdValue = (sample.sample as SampleView).collection_id;
        if (!collectionIdValue) return null;

        goto(
            routeHelpers.toFramesDetails(
                collectionIdValue,
                sampleNext.sample_id,
                frameIndex + 1
            )
        );
    }

    function goToPreviousFrame() {
        if (frameIndex == null || !sample) return null;
        if (!frameAdjacents) return null;

        const samplePrevious = $frameAdjacents?.samplePrevious;
        if (!samplePrevious) return null;

        const collectionIdValue = (sample.sample as SampleView).collection_id;
        if (!collectionIdValue) return null;

        goto(
            routeHelpers.toFramesDetails(
                collectionIdValue,
                samplePrevious.sample_id,
                frameIndex - 1
            )
        );
    }

    const handleEscape = () => {
        goto(routeHelpers.toFrames(collectionId));
    };
</script>

<SampleDetailsPanel
    {collectionId}
    {sampleId}
    sampleURL={sample ? `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}` : ''}
    sample={$videoFrame.data?.sample
        ? {
              ...$videoFrame.data?.sample,
              width: $videoFrame.data.video.width,
              height: $videoFrame.data.video.height
          }
        : undefined}
    {refetch}
    {handleEscape}
>
    {#snippet breadcrumb({ collection: rootCollection })}
        <FrameDetailsBreadcrumb {rootCollection} {frameIndex} />
    {/snippet}
    {#snippet metadataValue()}
        {#if $videoFrame.data}
            <FrameDetailsSegment sample={$videoFrame.data} />
            <MetadataSegment metadata_dict={($videoFrame.data.sample as SampleView).metadata_dict} />
        {/if}
    {/snippet}
    {#snippet children()}
        {#if frameAdjacents}
            <SteppingNavigation
                hasPrevious={!!$frameAdjacents?.samplePrevious}
                hasNext={!!$frameAdjacents?.sampleNext}
                onPrevious={goToPreviousFrame}
                onNext={goToNextFrame}
            />
        {/if}
    {/snippet}
</SampleDetailsPanel>
