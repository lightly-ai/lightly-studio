import type {
    EvaluationMetricSortExpr,
    QueryExpr,
    SortFieldExpr
} from '$lib/api/lightly_studio_local';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import type { MetadataValues } from '$lib/services/types';

export interface ClassifierSamples {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

export interface NormalModeFilters {
    annotation_label_ids?: string[];
    collection_ids?: string[];
    tag_ids?: string[];
    dimensions?: DimensionBounds;
    query_expr?: QueryExpr;
    sample_ids?: string[];
}

export interface CommonFilters {
    metadata_values?: MetadataValues;
    text_embedding?: number[];
}

export interface NormalModeParams {
    mode: 'normal';
    filters?: NormalModeFilters;
}

interface ClassifierModeParams {
    mode: 'classifier';
    classifierSamples?: ClassifierSamples;
}

export type ImagesInfiniteParams = {
    query_expr?: QueryExpr;
    collection_id: string;
    sort_by?: SortExpr[] | null;
} & (NormalModeParams | ClassifierModeParams) &
    CommonFilters;

export type SamplesQueryKey = readonly [
    string,
    string,
    'normal' | 'classifier',
    NormalModeFilters | ClassifierSamples | undefined,
    {
        metadata_values?: MetadataValues;
        text_embedding?: number[];
    },
    SortExpr[] | null | undefined
];

export type SortExpr = SortFieldExpr | ({ source: 'evaluation_metric' } & EvaluationMetricSortExpr);
