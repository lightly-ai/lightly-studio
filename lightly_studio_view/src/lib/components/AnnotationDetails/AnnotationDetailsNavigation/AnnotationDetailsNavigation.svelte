<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';

    const annotationIndex = $derived(page.data.annotationIndex);
    const annotationAdjacents = $derived(page.data.annotationAdjacents);
    const collectionId = page.data.collectionId;
    const gotoNextAnnotation = () => {
        if ($annotationAdjacents.annotationNext) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    collectionId: collectionId,
                    sampleId: $annotationAdjacents.annotationNext.parent_sample_id,
                    annotationId: $annotationAdjacents.annotationNext.sample_id,
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
                    collectionId: collectionId,
                    sampleId: $annotationAdjacents.annotationPrevious.parent_sample_id,
                    annotationId: $annotationAdjacents.annotationPrevious.sample_id,
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
    <div data-testid="annotation-navigation">
        <SteppingNavigation
            hasPrevious={!!$annotationAdjacents.annotationPrevious}
            hasNext={!!$annotationAdjacents.annotationNext}
            onPrevious={gotoPreviousAnnotation}
            onNext={gotoNextAnnotation}
        />
    </div>
{/if}

<svelte:window onkeydown={handleKeyDownEvent} />
