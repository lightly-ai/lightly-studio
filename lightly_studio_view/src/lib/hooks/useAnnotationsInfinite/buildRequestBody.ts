import type { ReadAnnotationsWithPayloadRequest } from '$lib/api/lightly_studio_local';
import type { AnnotationsInfiniteParams } from './types';

const DEFAULT_PAGE_LIMIT = 100;

export const buildRequestBody = (
    params: AnnotationsInfiniteParams,
    cursor: number
): ReadAnnotationsWithPayloadRequest => ({
    pagination: {
        cursor,
        limit: params.limit ?? DEFAULT_PAGE_LIMIT
    },
    annotation_label_ids: params.annotation_label_ids,
    tag_ids: params.tag_ids,
    sample_ids: params.sample_ids,
    text_embedding: params.text_embedding
});
