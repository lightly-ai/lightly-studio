import { derived, get, writable } from 'svelte/store';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type {
    AnnotationsFilter,
    EmbeddingRegion,
    SampleFilter,
    VideoFilter,
    VideoFieldsBoundsView,
    VideoSortFieldExpr
} from '$lib/api/lightly_studio_local';
import type { CategoricalMetadataValues } from '$lib/services/types';
import type { useImageFilters } from '$lib/hooks';
type QueryExpression = NonNullable<
    Parameters<ReturnType<typeof useImageFilters>['updateQueryExpr']>[0]
>;
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
const videoQueryExpression = writable<QueryExpression | null>(null);

export const buildVideoFilter = (
    $filterParams: VideoFilterParams | null,
    queryExpression?: QueryExpression | null
): VideoFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const filters = buildVideoBounds($filterParams.video_bounds);
    const sampleFilter = buildSampleFilter($filterParams.filters ?? {});
    if (queryExpression?.query_expr) {
        sampleFilter.query_expr = queryExpression.query_expr;
    }
    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }
    const annotationFramesLabelIds = $filterParams.filters?.annotation_frames_label_ids;
    if (annotationFramesLabelIds?.length) {
        filters.frame_annotation_filter = {
            filter_type: 'annotations',
            annotation_label_ids: annotationFramesLabelIds
        } satisfies AnnotationsFilter;
    }
    return filters;
};

const buildVideoBounds = (bounds: VideoFilterParams['video_bounds']): VideoFilter => {
    const filters: VideoFilter = { filter_type: 'video' };
    if (!bounds) return filters;
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
    if (bounds.fps) filters.fps = bounds.fps;
    if (bounds.duration_s) filters.duration_s = bounds.duration_s;
    return filters;
};

const buildSampleFilter = (filters: NonNullable<VideoFilterParams['filters']>): SampleFilter => {
    const sampleFilter = buildMetadataFilter(filters);
    if (filters.sample_ids?.length) sampleFilter.sample_ids = filters.sample_ids;
    if (filters.embedding_region) sampleFilter.embedding_region = filters.embedding_region;
    if (filters.tag_ids?.length) sampleFilter.tag_ids = filters.tag_ids;
    return sampleFilter;
};

const buildMetadataFilter = (filters: NonNullable<VideoFilterParams['filters']>): SampleFilter => {
    if (!filters.metadata_values && !filters.categorical_metadata_values) return {};
    const metadataFilters = createMetadataFilters(
        filters.metadata_values ?? {},
        filters.categorical_metadata_values ?? {}
    );
    return metadataFilters.length > 0 ? { metadata_filters: metadataFilters } : {};
};

const videoFilter = derived(
    [filterParams, videoQueryExpression],
    ([$filterParams, $videoQueryExpression]) =>
        buildVideoFilter($filterParams, $videoQueryExpression)
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
        if (params?.collection_id !== get(filterParams)?.collection_id) {
            videoQueryExpression.set(null);
        }
        filterParams.set(params);
    };

    const updateQueryExpr = (expr?: QueryExpression) => {
        videoQueryExpression.set(expr ?? null);
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
        videoQueryExpression,
        updateQueryExpr,
        filterParams,
        videoFilter,
        videoSortBy,
        updateFilterParams,
        updateSampleIds,
        updateEmbeddingRegion,
        updateSortBy
    };
};
