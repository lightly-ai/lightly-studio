import type { VideoFrameAnnotationsCounterFilter } from '$lib/api/lightly_studio_local';
import { countVideoFrameAnnotationsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { derived } from 'svelte/store';

type UseVideoFrameAnnotationCountsParams = {
    collectionId: string;
    filter: VideoFrameAnnotationsCounterFilter;
    enabled?: boolean;
};

export const useVideoFrameAnnotationCounts = (
    params: StoreOrVal<UseVideoFrameAnnotationCountsParams>
) => {
    const optionsStore = derived(toReadable(params), (currentParams) => ({
        ...countVideoFrameAnnotationsOptions({
            path: { video_frame_collection_id: currentParams.collectionId },
            body: {
                filter: currentParams.filter
            }
        }),
        enabled: currentParams.enabled ?? true
    }));
    return createQuery(optionsStore);
};
