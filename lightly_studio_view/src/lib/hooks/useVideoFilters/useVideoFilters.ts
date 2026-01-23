import { derived, get, writable } from 'svelte/store';
import type { components } from '$lib/schema';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type { VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { VideoFieldsBoundsView } from '$lib/api/lightly_studio_local/types.gen';

type SampleFilter = components['schemas']['SampleFilter'];
type MetadataValues = Record<string, { min: number; max: number }>;

export type VideoFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_frames_label_ids?: string[];
        sample_ids?: string[];
        metadata_values?: MetadataValues;
    };
    video_bounds?: VideoFieldsBoundsView | null;
    text_embedding?: Array<number>;
};

const filterParams = writable<VideoFilterParams | null>(null);

const videoFilter = derived(filterParams, ($filterParams): VideoFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const filters: VideoFilter = { type: 'video' };

    // Add video-specific bounds (width, height, fps, duration_s)
    if ($filterParams.video_bounds) {
        const bounds = $filterParams.video_bounds;

        // Convert IntRange to FilterDimensions for width/height
        if (bounds.width) {
            filters.width = {
                min: bounds.width.min ?? undefined,
                max: bounds.width.max ?? undefined
            };
        }

        if (bounds.height) {
            filters.height = {
                min: bounds.height.min ?? undefined,
                max: bounds.height.max ?? undefined
            };
        }

        // FloatRange is compatible directly
        if (bounds.fps) {
            filters.fps = bounds.fps;
        }

        if (bounds.duration_s) {
            filters.duration_s = bounds.duration_s;
        }
    }

    const sampleFilter: SampleFilter = {};
    sampleFilter.collection_id = $filterParams.collection_id;

    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const annotationFramesLabelIds = $filterParams.filters?.annotation_frames_label_ids;
    if (annotationFramesLabelIds && annotationFramesLabelIds.length > 0) {
        filters.annotation_frames_label_ids = annotationFramesLabelIds;
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

export const useVideoFilters = () => {
    const updateFilterParams = (params: VideoFilterParams) => {
        filterParams.set(params);
    };

    // updates only sample ids in the existing filter params
    const updateSampleIds = (sampleIds: string[]) => {
        const params = get(filterParams);
        if (!params || !params.collection_id) {
            // If filterParams is not initialized, we can't update sample_ids
            // This should not happen in normal flow, but we handle it gracefully
            return;
        }

        const newParams: VideoFilterParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };

        // Set the new params - this will trigger the videoFilter derived store to update
        filterParams.set(newParams);
    };

    return {
        filterParams,
        videoFilter,
        updateFilterParams,
        updateSampleIds
    };
};
