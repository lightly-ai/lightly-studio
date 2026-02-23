<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useAdjacentVideos } from '$lib/hooks/useAdjacentVideos/useAdjacentVideos';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '../SteppingNavigation/SteppingNavigation.svelte';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id);
    const sampleId = $derived(page.params.sample_id);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentVideos({
            sampleId
        })
    );

    const sampleAdjacentData = $derived($sampleAdjacentQuery.data);

    function goToNextVideo() {
        if (!sampleAdjacentData) return null;

        const sampleNext = sampleAdjacentData?.next_sample_id;
        if (!sampleNext) return null;

        goto(routeHelpers.toVideosDetails(datasetId, collectionType, collectionId, sampleNext));
    }

    function goToPreviousVideo() {
        if (!sampleAdjacentData) return null;

        const samplePrevious = sampleAdjacentData?.previous_sample_id;
        if (!samplePrevious) return null;

        goto(routeHelpers.toVideosDetails(datasetId, collectionType, collectionId, samplePrevious));
    }
</script>

{#if sampleAdjacentData}
    <SteppingNavigation
        hasPrevious={!!sampleAdjacentData.previous_sample_id}
        hasNext={!!sampleAdjacentData.next_sample_id}
        onPrevious={goToPreviousVideo}
        onNext={goToNextVideo}
    />
{/if}
