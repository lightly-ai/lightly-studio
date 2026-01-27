import { get, writable } from 'svelte/store';
import type { PageLoad } from './$types';
import {
    useAnnotationAdjacents,
    type UseAnnotationAdjacentsData
} from '$lib/hooks/useAnnotationAdjacents/useAnnotationAdjacents';

export const load: PageLoad = async ({
    parent,
    params: { collection_id, annotationId, annotationIndex: annotationIndexParam }
}) => {
    const { annotationsSelectedTagsIds, annotationsSelectedAnnotationLabelsIds, collection } =
        await parent();

    const annotationIndex = parseInt(annotationIndexParam, 10);

    const annotationAdjacentsData = writable<UseAnnotationAdjacentsData | undefined>();

    if (!collection) {
        throw new Error('Collection data not found');
    }

    useAnnotationAdjacents({
        annotationIndex,
        collection_id,
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
        collection
    };
};
