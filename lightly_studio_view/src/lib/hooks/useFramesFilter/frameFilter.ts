import {
    buildGridFilter,
    buildSampleFilter,
    toMetadataFilters,
    toRange
} from '$lib/utils/gridFilter';
import type {
    VideoFrameFilter,
    VideoFrameFieldsBoundsView
} from '$lib/api/lightly_studio_local/types.gen';
import type { CategoricalMetadataValues } from '$lib/services/types';
type MetadataValues = Record<string, { min: number; max: number }>;

export type VideoFrameFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_label_ids?: string[];
        sample_ids?: string[];
        metadata_values?: MetadataValues;
        categorical_metadata_values?: CategoricalMetadataValues;
    };
    frame_bounds?: VideoFrameFieldsBoundsView | null;
    video_id?: string | null;
};

export const getFrameFilter = (params: VideoFrameFilterParams | null): VideoFrameFilter | null => {
    if (!params?.collection_id) {
        return null;
    }

    const f = params.filters ?? {};

    return buildGridFilter(
        'video_frame',
        {
            video_id: params.video_id || undefined,
            frame_number: toRange(params.frame_bounds?.frame_number) ?? {}
        },
        buildSampleFilter({
            sample_ids: f.sample_ids,
            annotation_label_ids: f.annotation_label_ids,
            tag_ids: f.tag_ids,
            metadata_filters: toMetadataFilters(f.metadata_values, f.categorical_metadata_values)
        })
    );
};
