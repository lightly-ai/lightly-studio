import { createQuery } from '@tanstack/svelte-query';
import { countVideoFrameAnnotationsByVideoCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { type VideoCountAnnotationsFilter } from '$lib/api/lightly_studio_local';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { derived, type Readable } from 'svelte/store';

type UseVideoAnnotationCountsParams = {
    collectionId: string;
    filter: VideoCountAnnotationsFilter;
    enabled?: boolean;
};

const createVideoAnnotationCountsQueryOptions = ({
    collectionId,
    filter,
    enabled
}: UseVideoAnnotationCountsParams) => {
    return {
        ...countVideoFrameAnnotationsByVideoCollectionOptions({
            path: { collection_id: collectionId },
            body: {
                filter
            }
        }),
        enabled
    };
};

export const useVideoAnnotationCounts = (
    paramsInput: UseVideoAnnotationCountsParams | Readable<UseVideoAnnotationCountsParams>
) => {
    const options = isReadableStore<UseVideoAnnotationCountsParams>(paramsInput)
        ? derived(paramsInput, ($params) => createVideoAnnotationCountsQueryOptions($params))
        : createVideoAnnotationCountsQueryOptions(paramsInput);

    return createQuery(options);
};
