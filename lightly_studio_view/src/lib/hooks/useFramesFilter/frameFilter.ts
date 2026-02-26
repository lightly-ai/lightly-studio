import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type { components } from '$lib/schema';
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

export const getFrameFilter = (params: VideoFrameFilterParams | null): VideoFrameFilter | null => {
    if (!params?.collection_id) {
        return null;
    }

    const filters: VideoFrameFilter = {};

    if (params.video_id) {
        filters.video_id = params.video_id;
    }

    if (params.frame_bounds?.frame_number) {
        const frameNumber = params.frame_bounds.frame_number;
        filters.frame_number = {
            min: frameNumber.min ?? undefined,
            max: frameNumber.max ?? undefined
        };
    } else {
        filters.frame_number = {};
    }

    const sampleFilter: SampleFilter = {};
    sampleFilter.collection_id = params.collection_id;

    const sampleIds = params.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const annotationLabelIds = params.filters?.annotation_label_ids;
    if (annotationLabelIds && annotationLabelIds.length > 0) {
        sampleFilter.annotation_label_ids = annotationLabelIds;
    }

    const tagIds = params.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        sampleFilter.tag_ids = tagIds;
    }

    if (params.filters?.metadata_values) {
        const metadataFilters = createMetadataFilters(params.filters.metadata_values);
        if (metadataFilters.length > 0) {
            sampleFilter.metadata_filters = metadataFilters;
        }
    }

    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }

    return Object.keys(filters).length > 0 ? filters : null;
};
