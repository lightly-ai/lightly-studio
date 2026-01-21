import { goto } from '$app/navigation';
import { get, type Readable } from 'svelte/store';
import type { UseAnnotationAdjacentsData } from '../useAnnotationAdjacents/useAnnotationAdjacents';
import { routeHelpers } from '$lib/routes';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

export function useAnnotationDeleteNavigation({
    collectionId,
    annotationIndex,
    annotationAdjacents
}: {
    collectionId: string;
    annotationIndex: number;
    annotationAdjacents: Readable<UseAnnotationAdjacentsData>;
}) {
    const { setAnnotationId } = useAnnotationLabelContext();
    const { setStatus } = useSampleDetailsToolbarContext();

    const gotoNextAnnotation = () => {
        const index = annotationIndex;
        const adjacents = get(annotationAdjacents);

        if (adjacents.annotationNext) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    collectionId,
                    sampleId: adjacents.annotationNext.parent_sample_id,
                    annotationId: adjacents.annotationNext.sample_id,
                    annotationIndex: index + 1
                }),
                { invalidateAll: true }
            );
        } else {
            goto(routeHelpers.toAnnotations(collectionId));
        }

        setStatus('cursor');
        setAnnotationId(null);
    };

    return { gotoNextAnnotation };
}
