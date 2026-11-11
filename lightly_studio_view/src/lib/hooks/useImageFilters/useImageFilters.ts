import { derived, get, writable } from 'svelte/store';
import {
    buildGridFilter,
    buildSampleFilter,
    dimensionRanges,
    toMetadataFilters,
    patchFilters
} from '$lib/utils/gridFilter';
import type { ImagesInfiniteParams } from '../useImagesInfinite/useImagesInfinite';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type {
    ConfusionCell,
    EmbeddingRegion,
    ImageFilter,
    QueryExpr
} from '$lib/api/lightly_studio_local';
import type { ImageSortExpr } from '../useImagesInfinite/types';

const filterParams = writable<ImagesInfiniteParams>({} as ImagesInfiniteParams);

export interface QueryExpression {
    query_expr: QueryExpr;
    query_expr_str: string;
}

const imageQueryExpression = writable<QueryExpression | null>(null);

const imageFilter = derived(
    [filterParams, imageQueryExpression],
    ([$filterParams, $imageQueryExpression]): ImageFilter | null => {
        if (!$filterParams?.collection_id || $filterParams.mode !== 'normal') {
            return null;
        }

        const f = $filterParams.filters ?? {};

        return buildGridFilter(
            'image',
            dimensionRanges(f.dimensions),
            buildSampleFilter({
                sample_ids: f.sample_ids,
                // Embedding-plot lasso/rectangle selections are sent as geometry (a few KB) rather
                // than the full list of selected sample ids, so the request body stays
                // constant-size regardless of selection size (see LIG-9903). The backend
                // resolves the polygon to sample ids server-side.
                embedding_region: f.embedding_region,
                annotation_label_ids: f.annotation_label_ids,
                tag_ids: f.tag_ids,
                confusion_cell: f.confusion_cell,
                metadata_filters: toMetadataFilters(
                    $filterParams.metadata_values,
                    $filterParams.categorical_metadata_values
                ),
                query_expr: $imageQueryExpression?.query_expr
            })
        );
    }
);

const imageSortBy = writable<ImageSortExpr[] | null>([
    {
        source: 'image',
        field_name: 'file_path_abs',
        direction: SortDirection.ASC
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

        filterParams.set(
            patchFilters(params, { sample_ids: sampleIds.length > 0 ? sampleIds : undefined })
        );
    };

    // updates only the embedding-plot region selection in the existing filter params
    const updateEmbeddingRegion = (embeddingRegion: EmbeddingRegion | null) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        filterParams.set(patchFilters(params, { embedding_region: embeddingRegion ?? undefined }));
    };

    // updates only the confusion-matrix cell in the existing filter params
    const updateConfusionCell = (confusionCell: ConfusionCell | null) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        filterParams.set(patchFilters(params, { confusion_cell: confusionCell ?? undefined }));
    };

    const updateSortBy = (sort: ImageSortExpr[] | null) => {
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
