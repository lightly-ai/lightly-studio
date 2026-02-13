<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    const sampleIndex = $derived(page.data.sampleIndex);
    const sampleAdjacents = $derived(page.data.sampleAdjacents);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    const gotoNextSample = () => {
        if ($sampleAdjacents.sampleNext && datasetId && collectionType) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacents.sampleNext.sample_id,
                    datasetId,
                    collectionType,
                    collectionId: $sampleAdjacents.sampleNext.sample.collection_id,
                    sampleIndex: sampleIndex + 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousSample = () => {
        if ($sampleAdjacents.samplePrevious && datasetId && collectionType) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacents.samplePrevious.sample_id,
                    datasetId,
                    collectionType,
                    collectionId: $sampleAdjacents.samplePrevious.sample.collection_id,
                    sampleIndex: sampleIndex - 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const { context } = useAnnotationLabelContext();
</script>

{#if $sampleAdjacents}
    <SteppingNavigation
        hasPrevious={!!$sampleAdjacents.samplePrevious}
        hasNext={!!$sampleAdjacents.sampleNext}
        onPrevious={gotoPreviousSample}
        onNext={gotoNextSample}
        isDrawing={context?.isDrawing}
    />
{/if}
