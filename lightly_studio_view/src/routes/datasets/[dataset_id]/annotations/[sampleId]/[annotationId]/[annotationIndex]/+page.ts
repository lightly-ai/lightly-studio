import { get, writable } from 'svelte/store';
import type { PageLoad } from './$types';
import {
    useAnnotationAdjacents,
    type UseAnnotationAdjacentsData
} from '$lib/hooks/useAnnotationAdjacents/useAnnotationAdjacents';

export const load: PageLoad = async ({
    parent,
    params: { dataset_id, annotationId, annotationIndex: annotationIndexParam }
}) => {
    const { annotationsSelectedTagsIds, annotationsSelectedAnnotationLabelsIds, dataset } =
        await parent();

    const annotationIndex = parseInt(annotationIndexParam, 10);

    const annotationAdjacentsData = writable<UseAnnotationAdjacentsData | undefined>();

    if (!dataset) {
        throw new Error('Dataset data not found');
    }

    useAnnotationAdjacents({
        annotationIndex,
        dataset_id,
        currentAnnotationId: annotationId,
        annotation_label_ids: Array.from(get(annotationsSelectedAnnotationLabelsIds)),
        tag_ids: Array.from(get(annotationsSelectedTagsIds))
    }).subscribe(({ data }) => {
        annotationAdjacentsData.set(data);
    });

    return {
        annotationAdjacents: annotationAdjacentsData,
        annotationIndex,
        annotationId,
        dataset
    };
};
