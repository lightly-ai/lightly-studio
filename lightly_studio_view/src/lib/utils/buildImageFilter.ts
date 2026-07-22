import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import {
    type AnnotationsFilter,
    type ConfusionCell,
    type ImageFilter,
    type QueryExpr
} from '$lib/api/lightly_studio_local/types.gen.js';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';

type MetadataFilters = ReturnType<typeof createMetadataFilters>;

export function buildImageFilter({
    dimensionsValues,
    annotationFilter,
    metadataFilters,
    sampleIds,
    tagIds,
    confusionCell,
    queryExpr
}: {
    dimensionsValues: DimensionBounds | null | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    metadataFilters: MetadataFilters | undefined;
    sampleIds?: string[];
    tagIds?: string[];
    confusionCell?: ConfusionCell | null;
    queryExpr?: QueryExpr | null;
}): ImageFilter | undefined {
    const filter: ImageFilter = {};

    if (dimensionsValues) {
        if (dimensionsValues.min_width !== undefined || dimensionsValues.max_width !== undefined) {
            filter.width = {
                min: dimensionsValues.min_width,
                max: dimensionsValues.max_width
            };
        }
        if (
            dimensionsValues.min_height !== undefined ||
            dimensionsValues.max_height !== undefined
        ) {
            filter.height = {
                min: dimensionsValues.min_height,
                max: dimensionsValues.max_height
            };
        }
    }

    if (annotationFilter) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            annotations_filter: annotationFilter
        };
    }

    if (metadataFilters) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            metadata_filters: metadataFilters
        };
    }

    if (sampleIds && sampleIds.length > 0) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            sample_ids: sampleIds
        };
    }

    if (tagIds && tagIds.length > 0) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            tag_ids: tagIds
        };
    }

    if (confusionCell) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            confusion_cell: confusionCell
        };
    }

    if (queryExpr) {
        filter.sample_filter = {
            ...(filter.sample_filter ?? {}),
            query_expr: queryExpr
        };
    }

    return Object.keys(filter).length > 0 ? filter : undefined;
}
