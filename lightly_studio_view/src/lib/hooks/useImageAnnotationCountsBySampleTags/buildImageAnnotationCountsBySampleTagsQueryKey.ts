import { countImageAnnotationsBySampleTagsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useImageAnnotationCountsQueryKey } from '../useImageAnnotationCounts/useImageAnnotationCounts';
import {
    buildImageAnnotationCountsBySampleTagsRequest,
    type GroupedAnnotationCountsParams
} from './buildImageAnnotationCountsBySampleTagsRequest';

export function buildImageAnnotationCountsBySampleTagsQueryKey(
    params: GroupedAnnotationCountsParams
): ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey> {
    return [
        ...useImageAnnotationCountsQueryKey,
        'by-sample-tags',
        buildImageAnnotationCountsBySampleTagsRequest(params)
    ] as unknown as ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey>;
}
