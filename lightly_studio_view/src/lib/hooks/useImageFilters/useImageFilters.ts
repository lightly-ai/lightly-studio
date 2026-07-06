import { derived, get, writable } from 'svelte/store';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type { ImagesInfiniteParams } from '../useImagesInfinite/useImagesInfinite';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type {
    AnnotationsFilter,
    ConfusionCell,
    EmbeddingRegion,
    ImageFilter,
    QueryExpr,
    SampleFilter
} from '$lib/api/lightly_studio_local';
import type { SortExpr } from '../useImagesInfinite/types';

const filterParams = writable<ImagesInfiniteParams>({} as ImagesInfiniteParams);

const buildFilterDimensions = (min?: number, max?: number) => {
    if (min == null && max == null) {
        return undefined;
    }
    return {
        min: min ?? undefined,
        max: max ?? undefined
    };
};

const extractDimensions = (dimensions?: DimensionBounds) => {
    if (!dimensions) {
        return {};
    }

    const width = buildFilterDimensions(dimensions.min_width, dimensions.max_width);
    const height = buildFilterDimensions(dimensions.min_height, dimensions.max_height);

    return {
        width,
        height
    };
};

export interface QueryExpression {
    query_expr: QueryExpr;
    query_expr_str: string;
}

const imageQueryExpression = writable<QueryExpression | null>(null);

const imageFilter = derived(
    [filterParams, imageQueryExpression],
    ([$filterParams, $imageQueryExpression]): ImageFilter | null => {
        if (!$filterParams?.collection_id || !$filterParams?.mode) {
            return null;
        }

        if ($filterParams.mode === 'classifier') {
            return null;
        }

        const filters: ImageFilter = {
            filter_type: 'image'
        };

        const { width, height } = extractDimensions($filterParams.filters?.dimensions);
        if (width) {
            filters.width = width;
        }
        if (height) {
            filters.height = height;
        }

        const sampleFilter: SampleFilter = {};

        const sampleIds = $filterParams.filters?.sample_ids;
        if (sampleIds && sampleIds.length > 0) {
            sampleFilter.sample_ids = sampleIds;
        }

        // Embedding-plot lasso/rectangle selections are sent as geometry (a few KB) rather
        // than the full list of selected sample ids, so the request body stays constant-size
        // regardless of selection size (see LIG-9903). The backend resolves the polygon to
        // sample ids server-side.
        const embeddingRegion = $filterParams.filters?.embedding_region;
        if (embeddingRegion) {
            sampleFilter.embedding_region = embeddingRegion;
        }

        const annotationLabelIds = $filterParams.filters?.annotation_label_ids;
        if (annotationLabelIds && annotationLabelIds.length > 0) {
            sampleFilter.annotations_filter = {
                filter_type: 'annotations',
                annotation_label_ids: annotationLabelIds
            } satisfies AnnotationsFilter;
        }

        const tagIds = $filterParams.filters?.tag_ids;
        if (tagIds && tagIds.length > 0) {
            sampleFilter.tag_ids = tagIds;
        }

        const confusionCell = $filterParams.filters?.confusion_cell;
        if (confusionCell) {
            sampleFilter.confusion_cell = confusionCell;
        }

        if ($filterParams.metadata_values) {
            const metadataFilters = createMetadataFilters($filterParams.metadata_values);
            if (metadataFilters.length > 0) {
                sampleFilter.metadata_filters = metadataFilters;
            }
        }

        if ($imageQueryExpression?.query_expr) {
            sampleFilter.query_expr = $imageQueryExpression.query_expr;
        }

        if (Object.keys(sampleFilter).length > 0) {
            filters.sample_filter = sampleFilter;
        }

        return Object.keys(filters).length > 0 ? filters : null;
    }
);

const imageSortBy = writable<SortExpr[] | null>([
    {
        source: 'image',
        field_name: 'file_path_abs',
        direction: SortDirection.ASC,
        is_numeric: false
    }
]);

export const useImageFilters = () => {
    const updateFilterParams = (params: ImagesInfiniteParams) => {
        filterParams.set(params);
    };

    const updateQueryExpr = (expr?: QueryExpression) => {
        imageQueryExpression.set(expr ?? null);
    };

    // updates only sample ids in the existing filter params
    const updateSampleIds = (sampleIds: string[]) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        const newParams: ImagesInfiniteParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };

        filterParams.set(newParams);
    };

    // updates only the embedding-plot region selection in the existing filter params
    const updateEmbeddingRegion = (embeddingRegion: EmbeddingRegion | null) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        const newParams: ImagesInfiniteParams = {
            ...params,
            filters: {
                ...params.filters,
                embedding_region: embeddingRegion ?? undefined
            }
        };

        filterParams.set(newParams);
    };

    // updates only the confusion-matrix cell in the existing filter params
    const updateConfusionCell = (confusionCell: ConfusionCell | null) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        const newParams: ImagesInfiniteParams = {
            ...params,
            filters: {
                ...params.filters,
                confusion_cell: confusionCell ?? undefined
            }
        };

        filterParams.set(newParams);
    };

    const updateSortBy = (sort: SortExpr[] | null) => {
        imageSortBy.set(sort);
    };

    return {
        imageQueryExpression,
        filterParams,
        imageFilter,
        imageSortBy,
        updateFilterParams,
        updateQueryExpr,
        updateSampleIds,
        updateEmbeddingRegion,
        updateConfusionCell,
        updateSortBy
    };
};
