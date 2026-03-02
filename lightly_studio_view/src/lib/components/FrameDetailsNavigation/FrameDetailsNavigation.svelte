<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAdjacentFrames } from '$lib/hooks/useAdjacentFrames/useAdjacentFrames';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '../SteppingNavigation/SteppingNavigation.svelte';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id);
    const sampleId = $derived(page.params.sample_id);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentFrames({
            sampleId,
            collectionId
        })
    );

    const sampleAdjacentData = $derived($sampleAdjacentQuery.data);

    function goToNextFrame() {
        const sampleNext = sampleAdjacentData?.next_sample_id;
        if (!sampleNext) return;

        goto(routeHelpers.toFramesDetails(datasetId, collectionType, collectionId, sampleNext));
    }

    function goToPreviousFrame() {
        const samplePrevious = sampleAdjacentData?.previous_sample_id;
        if (!samplePrevious) return;

        goto(routeHelpers.toFramesDetails(datasetId, collectionType, collectionId, samplePrevious));
    }

    const { context } = useAnnotationLabelContext();
</script>

{#if sampleAdjacentData}
    <SteppingNavigation
        hasPrevious={!!sampleAdjacentData.previous_sample_id}
        hasNext={!!sampleAdjacentData.next_sample_id}
        onPrevious={goToPreviousFrame}
        onNext={goToNextFrame}
        isDrawing={context.isDrawing}
    />
{/if}
