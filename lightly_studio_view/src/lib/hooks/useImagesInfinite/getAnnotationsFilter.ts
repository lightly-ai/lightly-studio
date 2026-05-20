import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';

type AnnotationsFilterInput = {
    annotations_filter?: AnnotationsFilter;
    annotation_label_ids?: AnnotationsFilter['annotation_label_ids'];
    collection_ids?: AnnotationsFilter['collection_ids'];
};

export const getAnnotationsFilter = (
    filters: AnnotationsFilterInput
): AnnotationsFilter | undefined => {
    if (filters.annotations_filter) {
        return filters.annotations_filter;
    }

    const annotation_label_ids = filters.annotation_label_ids?.length
        ? filters.annotation_label_ids
        : undefined;
    const collection_ids = filters.collection_ids?.length ? filters.collection_ids : undefined;
    if (!annotation_label_ids && !collection_ids) return undefined;
    return {
        filter_type: 'annotations',
        ...(annotation_label_ids && { annotation_label_ids }),
        ...(collection_ids && { collection_ids })
    };
};
