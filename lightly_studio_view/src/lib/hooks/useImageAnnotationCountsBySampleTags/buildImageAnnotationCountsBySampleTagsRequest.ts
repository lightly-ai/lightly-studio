import type {
    AnnotationCountMode,
    AnnotationType,
    ImageFilter
} from '$lib/api/lightly_studio_local';

interface GroupedAnnotationCountsParams {
    /** ID of the collection to query. */
    collectionId: string;
    /** Ordered sample tag IDs whose counts are fetched independently. */
    sampleTagIds: string[];
    /** Optional image filter applied on top of each tag's membership. */
    filter?: ImageFilter;
    /** Restrict counts to a single annotation type, e.g. classification. */
    annotationType?: AnnotationType;
    /** Whether to count annotation objects or distinct annotated samples. */
    countMode?: AnnotationCountMode;
}

export function buildImageAnnotationCountsBySampleTagsRequest({
    collectionId,
    sampleTagIds,
    filter,
    annotationType,
    countMode
}: GroupedAnnotationCountsParams) {
    return {
        path: { collection_id: collectionId },
        body: {
            sample_tag_ids: sampleTagIds,
            ...(filter ? { filter } : {}),
            ...(annotationType ? { annotation_type: annotationType } : {}),
            ...(countMode ? { count_mode: countMode } : {})
        }
    };
}
