import { derived, get, writable } from 'svelte/store';
import type { components } from '$lib/schema';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type {
    VideoFrameFilter,
    VideoFrameFieldsBoundsView
} from '$lib/api/lightly_studio_local/types.gen';

type SampleFilter = components['schemas']['SampleFilter'];
type MetadataValues = Record<string, { min: number; max: number }>;
export type VideoFrameFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_label_ids?: string[];
        sample_ids?: string[];
        metadata_values?: MetadataValues;
    };
    frame_bounds?: VideoFrameFieldsBoundsView | null;
    video_id?: string | null;
};

const filterParams = writable<VideoFrameFilterParams | null>(null);

const frameFilter = derived(filterParams, ($filterParams): VideoFrameFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const filters: VideoFrameFilter = {};

    if ($filterParams.video_id) {
        filters.video_id = $filterParams.video_id;
    }

    if ($filterParams.frame_bounds?.frame_number) {
        const frameNumber = $filterParams.frame_bounds.frame_number;
        filters.frame_number = {
            min: frameNumber.min ?? undefined,
            max: frameNumber.max ?? undefined
        };
    } else {
        filters.frame_number = {};
    }

    const sampleFilter: SampleFilter = {};
    sampleFilter.collection_id = $filterParams.collection_id;

    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const annotationLabelIds = $filterParams.filters?.annotation_label_ids;
    if (annotationLabelIds && annotationLabelIds.length > 0) {
        sampleFilter.annotation_label_ids = annotationLabelIds;
    }

    const tagIds = $filterParams.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        sampleFilter.tag_ids = tagIds;
    }

    if ($filterParams.filters?.metadata_values) {
        const metadataFilters = createMetadataFilters($filterParams.filters.metadata_values);
        if (metadataFilters.length > 0) {
            sampleFilter.metadata_filters = metadataFilters;
        }
    }

    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }

    return Object.keys(filters).length > 0 ? filters : null;
});

export const useFramesFilter = () => {
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
