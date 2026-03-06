import type { VideoFrameAnnotationsCounterFilter } from '$lib/api/lightly_studio_local';
import { countVideoFrameAnnotationsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { createQuery } from '@tanstack/svelte-query';
import { derived, type Readable } from 'svelte/store';

type UseVideoFrameAnnotationCountsParams = {
    collectionId: string;
    filter: VideoFrameAnnotationsCounterFilter;
    enabled?: boolean;
};

const createVideoFrameAnnotationCountsQueryOptions = ({
    collectionId,
    filter,
    enabled
}: UseVideoFrameAnnotationCountsParams) => {
    return {
        ...countVideoFrameAnnotationsOptions({
            path: { video_frame_collection_id: collectionId },
            body: {
                filter
            }
        }),
        enabled
    };
};

export const useVideoFrameAnnotationCounts = (
    paramsInput:
        | UseVideoFrameAnnotationCountsParams
        | Readable<UseVideoFrameAnnotationCountsParams>
) => {
    const options = isReadableStore<UseVideoFrameAnnotationCountsParams>(paramsInput)
        ? derived(paramsInput, ($params) => createVideoFrameAnnotationCountsQueryOptions($params))
        : createVideoFrameAnnotationCountsQueryOptions(paramsInput);

    return createQuery(options);
};
