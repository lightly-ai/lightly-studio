<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAdjacentAnnotations } from '$lib/hooks/useAdjacentAnnotations/useAdjacentAnnotations';

    const collectionId = $derived(page.params.collection_id!);
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const annotationId = $derived(page.params.annotationId);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentAnnotations({
            sampleId: annotationId,
            collectionId
        })
    );

    const gotoNextAnnotation = () => {
        if ($sampleAdjacentQuery.data?.next_sample_id) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    collectionId,
                    annotationId: $sampleAdjacentQuery.data?.next_sample_id
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousAnnotation = () => {
        if ($sampleAdjacentQuery.data?.previous_sample_id) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    collectionId,
                    annotationId: $sampleAdjacentQuery.data?.previous_sample_id
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };
</script>

{#if $sampleAdjacentQuery.data}
    <div data-testid="annotation-navigation">
        <SteppingNavigation
            hasPrevious={!!$sampleAdjacentQuery.data?.previous_sample_id}
            hasNext={!!$sampleAdjacentQuery.data?.next_sample_id}
            onPrevious={gotoPreviousAnnotation}
            onNext={gotoNextAnnotation}
        />
    </div>
{/if}
