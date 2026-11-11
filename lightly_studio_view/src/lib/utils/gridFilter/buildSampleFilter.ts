import type {
    ConfusionCell,
    EmbeddingRegion,
    MetadataFilter,
    QueryExpr,
    SampleFilter
} from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import type { CategoricalMetadataValues, MetadataValues } from '$lib/services/types';
import { getAnnotationsFilter } from './getAnnotationsFilter';
import { withoutUndefined } from './withoutUndefined';

export interface SampleFilterParts {
    sample_ids?: string[] | null;
    tag_ids?: string[] | null;
    annotation_label_ids?: string[] | null;
    annotation_collection_ids?: string[] | null;
    embedding_region?: EmbeddingRegion | null;
    confusion_cell?: ConfusionCell | null;
    metadata_filters?: MetadataFilter[] | null;
    query_expr?: QueryExpr | null;
}

const nonEmpty = <T>(list: T[] | null | undefined): T[] | undefined =>
    list?.length ? list : undefined;

/**
 * Builds the sample filter shared by all grid filters. Empty lists and `null` values are
 * left out. Returns `undefined` when nothing is left.
 */
export function buildSampleFilter(parts: SampleFilterParts): SampleFilter | undefined {
    const entries: SampleFilter = {
        sample_ids: nonEmpty(parts.sample_ids),
        tag_ids: nonEmpty(parts.tag_ids),
        annotations_filter: getAnnotationsFilter({
            annotation_label_ids: parts.annotation_label_ids,
            collection_ids: parts.annotation_collection_ids
        }),
        embedding_region: parts.embedding_region ?? undefined,
        confusion_cell: parts.confusion_cell ?? undefined,
        metadata_filters: nonEmpty(parts.metadata_filters),
        query_expr: parts.query_expr ?? undefined
    };
    const result = withoutUndefined(entries) as SampleFilter;
    return Object.keys(result).length > 0 ? result : undefined;
}

/** Creates metadata filters, or `undefined` when no values are set. */
export function toMetadataFilters(
    metadataValues?: MetadataValues,
    categoricalValues?: CategoricalMetadataValues
): MetadataFilter[] | undefined {
    if (!metadataValues && !categoricalValues) return undefined;
    return createMetadataFilters(metadataValues ?? {}, categoricalValues ?? {});
}
