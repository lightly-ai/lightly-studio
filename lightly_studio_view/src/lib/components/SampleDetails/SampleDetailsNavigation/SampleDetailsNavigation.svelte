<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAdjacentImages } from '$lib/hooks/useAdjacentImages/useAdjacentImages';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentImages({
            sampleId: page.params.sampleId,
            collectionId
        })
    );

    const gotoNextSample = () => {
        if ($sampleAdjacentQuery.data?.next_sample_id) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacentQuery.data?.next_sample_id,
                    datasetId,
                    collectionType,
                    collectionId: collectionId
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousSample = () => {
        if ($sampleAdjacentQuery.data?.previous_sample_id) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacentQuery.data?.previous_sample_id,
                    datasetId,
                    collectionType,
                    collectionId: collectionId
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const { context } = useAnnotationLabelContext();
</script>

{#if $sampleAdjacentQuery.data}
    <SteppingNavigation
        hasPrevious={!!$sampleAdjacentQuery.data?.previous_sample_id}
        hasNext={!!$sampleAdjacentQuery.data?.next_sample_id}
        onPrevious={gotoPreviousSample}
        onNext={gotoNextSample}
        isDrawing={context?.isDrawing}
    />
{/if}
