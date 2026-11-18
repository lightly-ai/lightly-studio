<script lang="ts">
    import { page } from '$app/state';
    import { goto, preloadData } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAdjacentImages } from '$lib/hooks/useAdjacentImages/useAdjacentImages';
    import {
        datasetNavOptions,
        toWorkflowSampleURL
    } from '$lib/components/Workflow/datasetNavigation';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id!);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentImages({
            sampleId: page.params.sampleId!,
            collectionId
        })
    );

    const nextURL = $derived.by(() => {
        if (sampleAdjacentQuery.data?.next_sample_id) {
            // A neighbour in a batch opens in workflow mode and keeps stepping in grid order.
            return toWorkflowSampleURL(
                routeHelpers.toSample({
                    sampleId: sampleAdjacentQuery.data.next_sample_id,
                    datasetId,
                    collectionType,
                    collectionId: collectionId
                }),
                sampleAdjacentQuery.data.next_workflow
            );
        }
        return null;
    });

    const gotoNextSample = () => {
        if (nextURL) {
            goto(nextURL, datasetNavOptions);
        }
    };

    const prevURL = $derived.by(() => {
        if (sampleAdjacentQuery.data?.previous_sample_id) {
            // A neighbour in a batch opens in workflow mode and keeps stepping in grid order.
            return toWorkflowSampleURL(
                routeHelpers.toSample({
                    sampleId: sampleAdjacentQuery.data.previous_sample_id,
                    datasetId,
                    collectionType,
                    collectionId: collectionId
                }),
                sampleAdjacentQuery.data.previous_workflow
            );
        }
        return null;
    });

    const gotoPreviousSample = () => {
        if (prevURL) {
            goto(prevURL, datasetNavOptions);
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
