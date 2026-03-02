import { derived, get, writable } from 'svelte/store';
import { getFrameFilter } from './frameFilter';
import type { VideoFrameFilterParams } from './frameFilter';

const filterParams = writable<VideoFrameFilterParams | null>(null);

const getFrameFilterStore = () => derived(filterParams, getFrameFilter);

export const useFramesFilter = () => {
    const frameFilter = getFrameFilterStore();

    const updateFilterParams = (params: VideoFrameFilterParams | null) => {
        filterParams.set(params);
    };

    const updateSampleIds = (sampleIds: string[]) => {
        const params = get(filterParams);
        if (!params || !params.collection_id) {
            return;
        }

        const newParams: VideoFrameFilterParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };
        filterParams.set(newParams);
    };

    return {
        filterParams,
        frameFilter,
        updateFilterParams,
        updateSampleIds
    };
};

export { getFrameFilter };
