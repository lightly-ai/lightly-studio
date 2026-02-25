import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { routeHelpers } from '$lib/routes';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAdjacentAnnotations } from '../useAdjacentAnnotations/useAdjacentAnnotations';

export function useAnnotationDeleteNavigation({
    annotationId,
    collectionId,
    datasetId,
    collectionType
}: {
    annotationId: string;
    collectionId: string;
    datasetId: string;
    collectionType: string;
}) {
    const { setAnnotationId } = useAnnotationLabelContext();
    const { setStatus } = useSampleDetailsToolbarContext();
    const { query: adjacentAnnotationsQuery } = useAdjacentAnnotations({
        sampleId: annotationId,
        collectionId
    });

    const gotoNextAnnotation = () => {
        const nextAnnotationId = get(adjacentAnnotationsQuery).data?.next_sample_id;

        if (nextAnnotationId) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionId,
                    collectionType,
                    annotationId: nextAnnotationId
                }),
                { invalidateAll: true }
            );
        } else {
            goto(routeHelpers.toAnnotations(datasetId, collectionType, collectionId));
        }

        setStatus('cursor');
        setAnnotationId(null);
    };

    return { gotoNextAnnotation };
}
