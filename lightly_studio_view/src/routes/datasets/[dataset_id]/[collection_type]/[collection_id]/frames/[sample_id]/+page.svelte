<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import { type SampleView } from '$lib/api/lightly_studio_local';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import FrameDetailsBreadcrumb from '$lib/components/FrameDetailsBreadcrumb/FrameDetailsBreadcrumb.svelte';
    import { useFrame } from '$lib/hooks/useFrame/useFrame';
    import FrameDetailsSegment from '$lib/components/frames/FrameDetailsSegment/FrameDetailsSegment.svelte';
    import SampleDetailsPanel from '$lib/components/SampleDetails/SampleDetailsPanel.svelte';
    import MetadataSegment from '$lib/components/MetadataSegment/MetadataSegment.svelte';
    import { page } from '$app/state';
    import VideoFrameNavigation from '$lib/components/VideoFrameNavigation/VideoFrameNavigation.svelte';

    const { data }: { data: PageData } = $props();
    const { frameIndex, frameAdjacents, collection_id, sampleId } = $derived(data);
    const { refetch, videoFrame } = $derived(useFrame(sampleId));

    const sample = $derived($videoFrame.data);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    function goToNextFrame() {
        if (frameIndex == null || !sample) return null;
        if (!frameAdjacents) return null;

        const sampleNext = $frameAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toFramesDetails(
                datasetId,
                collectionType,
                collection_id,
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

        goto(
            routeHelpers.toFramesDetails(
                datasetId,
                collectionType,
                collection_id,
                samplePrevious.sample_id,
                frameIndex - 1
            )
        );
    }

    const handleEscape = () => {
        goto(routeHelpers.toFrames(datasetId, collectionType, collection_id));
    };

    const sampleItem = $derived(
        $videoFrame.data?.sample
            ? {
                  ...$videoFrame.data?.sample,
                  width: $videoFrame.data.video.width,
                  height: $videoFrame.data.video.height
              }
            : undefined
    );
</script>

{#if sample && sampleItem}
    <SampleDetailsPanel
        dataTestId="video-frame-details"
        collectionId={collection_id}
        {sampleId}
        sampleURL={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}`}
        sample={sampleItem}
        {refetch}
        {handleEscape}
    >
        {#snippet breadcrumb({ collection: rootCollection })}
            <FrameDetailsBreadcrumb {rootCollection} {frameIndex} />
        {/snippet}

        {#snippet metadataValue()}
            {#if $videoFrame.data}
                <FrameDetailsSegment sample={$videoFrame.data} />
                <MetadataSegment
                    metadata_dict={($videoFrame.data.sample as SampleView).metadata_dict}
                />
            {/if}
        {/snippet}
        {#snippet children()}
            {#if frameAdjacents}
                <VideoFrameNavigation
                    hasPrevious={!!$frameAdjacents?.samplePrevious}
                    hasNext={!!$frameAdjacents?.sampleNext}
                    onPrevious={goToPreviousFrame}
                    onNext={goToNextFrame}
                />
            {/if}
        {/snippet}
    </SampleDetailsPanel>
{/if}
