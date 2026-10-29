<script lang="ts">
    import { page } from '$app/state';
    import { goto, preloadData } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAdjacentImages } from '$lib/hooks/useAdjacentImages/useAdjacentImages';
    import { getImageURLById } from '$lib/utils';
    import { preloadAdjacentImages, preloadImageUrl } from './preloadAdjacentImages';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id!);

    const { query: sampleAdjacentQuery, ensureAdjacent } = $derived(
        useAdjacentImages({
            sampleId: page.params.sampleId!,
            collectionId
        })
    );

    const nextURL = $derived.by(() => {
        if (sampleAdjacentQuery.data?.next_sample_id) {
            return routeHelpers.toSample({
                sampleId: sampleAdjacentQuery.data?.next_sample_id,
                datasetId,
                collectionType,
                collectionId: collectionId
            });
        }
        return null;
    });

    const gotoNextSample = () => {
        if (nextURL) {
            goto(nextURL);
        }
    };

    const prevURL = $derived.by(() => {
        if (sampleAdjacentQuery.data?.previous_sample_id) {
            return routeHelpers.toSample({
                sampleId: sampleAdjacentQuery.data?.previous_sample_id,
                datasetId,
                collectionType,
                collectionId: collectionId
            });
        }
        return null;
    });

    const gotoPreviousSample = () => {
        if (prevURL) {
            goto(prevURL);
        }
    };

    const { context } = useAnnotationLabelContext();

    $effect(() => {
        if (nextURL) {
            preloadData(nextURL);
        }
        if (prevURL) {
            preloadData(prevURL);
        }
    });

    // Full-size images of the next 3 and the previous sample, so stepping does not wait on them.
    const PRELOAD_NEXT_COUNT = 3;
    $effect(() => {
        const data = sampleAdjacentQuery.data;
        if (!data) return;
        let cancelled = false;
        preloadAdjacentImages({
            nextSampleId: data.next_sample_id,
            previousSampleId: data.previous_sample_id,
            nextCount: PRELOAD_NEXT_COUNT,
            getNextSampleId: async (sampleId) => (await ensureAdjacent(sampleId))?.next_sample_id,
            preloadImage: (sampleId) => preloadImageUrl(getImageURLById(sampleId)),
            isCancelled: () => cancelled
        });
        return () => {
            cancelled = true;
        };
    });
</script>

{#if sampleAdjacentQuery.data}
    <SteppingNavigation
        hasNext={nextURL !== null}
        hasPrevious={prevURL !== null}
        onPrevious={gotoPreviousSample}
        onNext={gotoNextSample}
        isDrawing={context?.isDrawing}
    />
{/if}
