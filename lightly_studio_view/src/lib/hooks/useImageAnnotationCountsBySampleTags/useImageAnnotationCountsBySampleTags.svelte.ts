import { createQuery } from '@tanstack/svelte-query';
import type { SampleTagAnnotationCountsView } from '$lib/api/lightly_studio_local';
import { countImageAnnotationsBySampleTagsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsBySampleTags } from '$lib/api/lightly_studio_local/sdk.gen';
import { buildImageAnnotationCountsBySampleTagsQueryKey } from './buildImageAnnotationCountsBySampleTagsQueryKey';
import {
    buildImageAnnotationCountsBySampleTagsRequest,
    type GroupedAnnotationCountsParams
} from './buildImageAnnotationCountsBySampleTagsRequest';

export { buildImageAnnotationCountsBySampleTagsQueryKey } from './buildImageAnnotationCountsBySampleTagsQueryKey';
export { buildImageAnnotationCountsBySampleTagsRequest } from './buildImageAnnotationCountsBySampleTagsRequest';
export type { GroupedAnnotationCountsParams } from './buildImageAnnotationCountsBySampleTagsRequest';

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
