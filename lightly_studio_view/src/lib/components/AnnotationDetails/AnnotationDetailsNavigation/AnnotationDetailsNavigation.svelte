<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';

    const annotationIndex = $derived(page.data.annotationIndex);
    const annotationAdjacents = $derived(page.data.annotationAdjacents);

    const gotoNextAnnotation = () => {
        if ($annotationAdjacents.annotationNext) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId: $annotationAdjacents.annotationNext.dataset_id,
                    sampleId: $annotationAdjacents.annotationNext.sample_id,
                    annotationId: $annotationAdjacents.annotationNext.annotation_id,
                    annotationIndex: annotationIndex + 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousAnnotation = () => {
        if ($annotationAdjacents.annotationPrevious) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId: $annotationAdjacents.annotationPrevious.dataset_id,
                    sampleId: $annotationAdjacents.annotationPrevious.sample_id,
                    annotationId: $annotationAdjacents.annotationPrevious.annotation_id,
                    annotationIndex: annotationIndex - 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const handleKeyDownEvent = (event: KeyboardEvent) => {
        switch (event.key) {
            case 'ArrowRight':
                gotoNextAnnotation();
                break;
            case 'ArrowLeft':
                gotoPreviousAnnotation();
                break;
        }
    };
</script>

{#if $annotationAdjacents}
    <SteppingNavigation
        hasPrevious={!!$annotationAdjacents.annotationPrevious}
        hasNext={!!$annotationAdjacents.annotationNext}
        onPrevious={gotoPreviousAnnotation}
        onNext={gotoNextAnnotation}
    />
{/if}

<svelte:window onkeydown={handleKeyDownEvent} />
