import { derived, get, writable } from 'svelte/store';
import {
    buildGridFilter,
    buildSampleFilter,
    getAnnotationsFilter,
    toMetadataFilters,
    toRange
} from '$lib/utils/gridFilter';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type {
    EmbeddingRegion,
    VideoFilter,
    VideoFieldsBoundsView,
    VideoSortFieldExpr
} from '$lib/api/lightly_studio_local';
import type { CategoricalMetadataValues } from '$lib/services/types';
type MetadataValues = Record<string, { min: number; max: number }>;

export type VideoFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_frames_label_ids?: string[];
        sample_ids?: string[];
        embedding_region?: EmbeddingRegion;
        metadata_values?: MetadataValues;
        categorical_metadata_values?: CategoricalMetadataValues;
    };
    video_bounds?: VideoFieldsBoundsView | null;
};

const filterParams = writable<VideoFilterParams | null>(null);

const videoBoundsFields = (
    bounds: VideoFieldsBoundsView | null | undefined
): Pick<VideoFilter, 'width' | 'height' | 'fps' | 'duration_s'> =>
    bounds
        ? {
              width: toRange(bounds.width),
              height: toRange(bounds.height),
              fps: bounds.fps,
              duration_s: bounds.duration_s
          }
        : {};

export const buildVideoFilter = ($filterParams: VideoFilterParams | null): VideoFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const f = $filterParams.filters ?? {};

    return buildGridFilter(
        'video',
        {
            ...videoBoundsFields($filterParams.video_bounds),
            frame_annotation_filter: getAnnotationsFilter({
                annotation_label_ids: f.annotation_frames_label_ids
            })
        },
        buildSampleFilter({
            sample_ids: f.sample_ids,
            embedding_region: f.embedding_region,
            tag_ids: f.tag_ids,
            metadata_filters: toMetadataFilters(f.metadata_values, f.categorical_metadata_values)
        })
    );
};

const videoFilter = derived(filterParams, ($filterParams): VideoFilter | null =>
    buildVideoFilter($filterParams)
);

const videoSortBy = writable<VideoSortFieldExpr[] | null>([
    {
        source: 'video',
        field_name: 'file_path_abs',
        direction: SortDirection.ASC
    }
]);

export const useVideoFilters = () => {
    const updateFilterParams = (params: VideoFilterParams) => {
        filterParams.set(params);
    };

    const updateSampleIds = (sampleIds: string[]) => {
        const params = get(filterParams);
        if (!params || !params.collection_id) {
            return;
        }

        const newParams: VideoFilterParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };
        filterParams.set(newParams);
    };

    const updateEmbeddingRegion = (embeddingRegion: EmbeddingRegion | null) => {
        const params = get(filterParams);
        if (!params?.collection_id) {
            return;
        }

        filterParams.set({
            ...params,
            filters: {
                ...params.filters,
                embedding_region: embeddingRegion ?? undefined
            }
        });
    };

    const updateSortBy = (sort: VideoSortFieldExpr[] | null) => {
        videoSortBy.set(sort);
    };

    return {
        filterParams,
        videoFilter,
        videoSortBy,
        updateFilterParams,
        updateSampleIds,
        updateEmbeddingRegion,
        updateSortBy
    };
};
