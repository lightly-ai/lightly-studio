import { countImageAnnotationsBySampleTagsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { buildImageAnnotationCountsBySampleTagsRequest } from './buildImageAnnotationCountsBySampleTagsRequest';

export function buildImageAnnotationCountsBySampleTagsQueryKey(
    params: Parameters<typeof buildImageAnnotationCountsBySampleTagsRequest>[0]
): ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey> {
    return [
        ...useImageAnnotationCountsQueryKey,
        'by-sample-tags',
        buildImageAnnotationCountsBySampleTagsRequest(params)
    ] as unknown as ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey>;
}
