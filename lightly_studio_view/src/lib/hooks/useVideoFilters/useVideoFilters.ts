import { derived, get, writable } from 'svelte/store';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type {
    AnnotationsFilter,
    QueryExpr,
    SampleFilter,
    VideoFilter,
    VideoFieldsBoundsView,
    VideoSortFieldExpr
} from '$lib/api/lightly_studio_local';
import type { CategoricalMetadataValues } from '$lib/services/types';
import type { QueryExpression } from '../useImageFilters/useImageFilters';
type MetadataValues = Record<string, { min: number; max: number }>;

export type VideoFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_frames_label_ids?: string[];
        sample_ids?: string[];
        metadata_values?: MetadataValues;
        categorical_metadata_values?: CategoricalMetadataValues;
        query_expr?: QueryExpr;
    };
    video_bounds?: VideoFieldsBoundsView | null;
};

const filterParams = writable<VideoFilterParams | null>(null);

export const buildVideoFilter = ($filterParams: VideoFilterParams | null): VideoFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const filters: VideoFilter = {
        filter_type: 'video'
    };

    // Add video-specific bounds (width, height, fps, duration_s)
    if ($filterParams.video_bounds) {
        const bounds = $filterParams.video_bounds;

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

        if (bounds.fps) {
            filters.fps = bounds.fps;
        }

        if (bounds.duration_s) {
            filters.duration_s = bounds.duration_s;
        }
    }

    const sampleFilter: SampleFilter = {};

    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const tagIds = $filterParams.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        sampleFilter.tag_ids = tagIds;
    }

    if (
        $filterParams.filters?.metadata_values ||
        $filterParams.filters?.categorical_metadata_values
    ) {
        const metadataFilters = createMetadataFilters(
            $filterParams.filters.metadata_values ?? {},
            $filterParams.filters.categorical_metadata_values ?? {}
        );
        if (metadataFilters.length > 0) {
            sampleFilter.metadata_filters = metadataFilters;
        }
    }

    const queryExpr = $filterParams.filters?.query_expr;
    if (queryExpr) {
        sampleFilter.query_expr = queryExpr;
    }

    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }
    const annotationFramesLabelIds = $filterParams.filters?.annotation_frames_label_ids;
    if (annotationFramesLabelIds && annotationFramesLabelIds.length > 0) {
        filters.frame_annotation_filter = {
            filter_type: 'annotations',
            annotation_label_ids: annotationFramesLabelIds
        } satisfies AnnotationsFilter;
    }

    return Object.keys(filters).length > 0 ? filters : null;
};

const videoFilter = derived(filterParams, ($filterParams): VideoFilter | null =>
    buildVideoFilter($filterParams)
);

const videoQueryExpression = writable<QueryExpression | null>(null);

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

    const updateSortBy = (sort: VideoSortFieldExpr[] | null) => {
        videoSortBy.set(sort);
    };

    const updateQueryExpr = (expr?: QueryExpression) => {
        videoQueryExpression.set(expr ?? null);
    };

    return {
        filterParams,
        videoFilter,
        videoSortBy,
        videoQueryExpression,
        updateFilterParams,
        updateSampleIds,
        updateSortBy,
        updateQueryExpr
    };
};
