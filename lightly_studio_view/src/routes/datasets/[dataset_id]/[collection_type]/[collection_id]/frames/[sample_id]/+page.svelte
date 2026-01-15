<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import { type SampleView } from '$lib/api/lightly_studio_local';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import FrameDetailsBreadcrumb from '$lib/components/FrameDetailsBreadcrumb/FrameDetailsBreadcrumb.svelte';
    import { useFrame } from '$lib/hooks/useFrame/useFrame';
    import FrameDetailsSegment from '$lib/components/frames/FrameDetailsSegment/FrameDetailsSegment.svelte';
    import SampleDetailsPanel from '$lib/components/SampleDetails/SampleDetailsPanel.svelte';
    import MetadataSegment from '$lib/components/MetadataSegment/MetadataSegment.svelte';
    import { page } from '$app/state';

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

        // Use the collection_id from the next sample
        const nextCollectionId = (sampleNext.sample as SampleView).collection_id;
        if (!nextCollectionId) return null;
        goto(
            routeHelpers.toFramesDetails(
                datasetId,
                collectionType,
                nextCollectionId,
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

        // Use the collection_id from the previous sample
        const previousCollectionId = (samplePrevious.sample as SampleView).collection_id;
        if (!previousCollectionId) return null;
        goto(
            routeHelpers.toFramesDetails(
                datasetId,
                collectionType,
                previousCollectionId,
                samplePrevious.sample_id,
                frameIndex - 1
            )
        );
    }

    const handleEscape = () => {
        goto(routeHelpers.toFrames(datasetId, collectionType, collection_id));
    };
</script>

<SampleDetailsPanel
    collectionId={collection_id}
    {sampleId}
    sampleURL={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}`}
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
        <FrameDetailsSegment sample={$videoFrame.data} />
        <MetadataSegment metadata_dict={($videoFrame.data.sample as SampleView).metadata_dict} />
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
