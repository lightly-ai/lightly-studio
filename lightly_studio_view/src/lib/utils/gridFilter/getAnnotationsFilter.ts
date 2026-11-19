import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';

type AnnotationsFilterInput = Pick<
    AnnotationsFilter,
    'annotation_label_ids' | 'collection_ids' | 'include_unannotated_samples'
>;

export const getAnnotationsFilter = (
    filters: AnnotationsFilterInput
): AnnotationsFilter | undefined => {
    const annotation_label_ids = filters.annotation_label_ids?.length
        ? filters.annotation_label_ids
        : undefined;
    const collection_ids = filters.collection_ids?.length ? filters.collection_ids : undefined;
    const include_unannotated_samples = filters.include_unannotated_samples || undefined;
    if (!annotation_label_ids && !collection_ids && !include_unannotated_samples) return undefined;
    return {
        filter_type: 'annotations',
        ...(annotation_label_ids && { annotation_label_ids }),
        ...(collection_ids && { collection_ids }),
        ...(include_unannotated_samples && { include_unannotated_samples })
    };
};
