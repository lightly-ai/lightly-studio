import { createQuery } from '@tanstack/svelte-query';
import type {
    AnnotationCountMode,
    AnnotationType,
    ImageFilter,
    SampleTagAnnotationCountsView
} from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsBySampleTagsOptions,
    countImageAnnotationsBySampleTagsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsBySampleTags } from '$lib/api/lightly_studio_local/sdk.gen';
import { useImageAnnotationCountsQueryKey } from '../useImageAnnotationCounts/useImageAnnotationCounts';

interface GroupedAnnotationCountsParams {
    collectionId: string;
    sampleTagIds: string[];
    filter?: ImageFilter;
    annotationType?: AnnotationType;
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

export function buildImageAnnotationCountsBySampleTagsQueryKey(
    params: GroupedAnnotationCountsParams
): ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey> {
    return [
        ...useImageAnnotationCountsQueryKey,
        'by-sample-tags',
        buildImageAnnotationCountsBySampleTagsRequest(params)
    ] as unknown as ReturnType<typeof countImageAnnotationsBySampleTagsQueryKey>;
}

export const useImageAnnotationCountsBySampleTags = (
    getParams: () => GroupedAnnotationCountsParams & { enabled?: boolean }
) => {
    return createQuery(() => {
        const { enabled, ...params } = getParams();
        const requestOptions = buildImageAnnotationCountsBySampleTagsRequest(params);

        return {
            ...countImageAnnotationsBySampleTagsOptions(requestOptions),
            queryKey: buildImageAnnotationCountsBySampleTagsQueryKey(params),
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await countImageAnnotationsBySampleTags({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            },
            enabled: (enabled ?? true) && params.sampleTagIds.length > 0,
            placeholderData: (previousData: SampleTagAnnotationCountsView[] | undefined) =>
                previousData
        };
    });
};
