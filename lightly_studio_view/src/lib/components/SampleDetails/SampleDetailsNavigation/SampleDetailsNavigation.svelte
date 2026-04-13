<script lang="ts">
    import { page } from '$app/state';
    import { goto, preloadData } from '$app/navigation';
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

    const nextURL = $derived.by(() => {
        if ($sampleAdjacentQuery.data?.next_sample_id) {
            return routeHelpers.toSample({
                sampleId: $sampleAdjacentQuery.data?.next_sample_id,
                datasetId,
                collectionType,
                collectionId: collectionId
            });
        }
        return null;
    });

    const gotoNextSample = () => {
        if (nextURL) {
            goto(nextURL, {
                invalidateAll: true
            });
        }
    };

    const prevURL = $derived.by(() => {
        if ($sampleAdjacentQuery.data?.previous_sample_id) {
            return routeHelpers.toSample({
                sampleId: $sampleAdjacentQuery.data?.previous_sample_id,
                datasetId,
                collectionType,
                collectionId: collectionId
            });
        }
        return null;
    });

    const gotoPreviousSample = () => {
        if (prevURL) {
            goto(prevURL, {
                invalidateAll: true
            });
        }
    };

    const { context } = useAnnotationLabelContext();
    const hasNext = $derived(!!$sampleAdjacentQuery.data?.next_sample_id);
    const hasPrevious = $derived(!!$sampleAdjacentQuery.data?.previous_sample_id);

    $effect(() => {
        if (nextURL) {
            console.log('Preloading next sample:', nextURL);
            preloadData(nextURL);
        }
        if (prevURL) {
            preloadData(prevURL);
            console.log('Preloading previous sample:', prevURL);
        }
    });
</script>

{#if $sampleAdjacentQuery.data}
    <SteppingNavigation
        {hasPrevious}
        {hasNext}
        onPrevious={gotoPreviousSample}
        onNext={gotoNextSample}
        isDrawing={context?.isDrawing}
    />
{/if}
