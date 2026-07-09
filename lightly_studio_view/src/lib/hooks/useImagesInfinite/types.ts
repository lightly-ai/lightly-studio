import type {
    AnnotationsFilter,
    EvaluationMetricSortExpr,
    QueryExpr,
    ReadImagesRequest,
    SampleFilter,
    SortFieldExpr
} from '$lib/api/lightly_studio_local';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import type { MetadataValues } from '$lib/services/types';

export interface ClassifierSamples {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

export type NormalModeFilters = Pick<AnnotationsFilter, 'annotation_label_ids' | 'collection_ids'> &
    Pick<SampleFilter, 'tag_ids' | 'sample_ids' | 'confusion_cell' | 'embedding_region'> & {
        dimensions?: DimensionBounds;
    };

export type ImagesInfiniteParams = {
    collection_id: string;
    query_expr?: QueryExpr;
    sort_by?: ReadImagesRequest['sort_by'];
    text_embedding?: ReadImagesRequest['text_embedding'];
    metadata_values?: MetadataValues;
} & (
    | { mode: 'normal'; filters?: NormalModeFilters }
    | { mode: 'classifier'; classifierSamples?: ClassifierSamples }
);

export type SamplesQueryKey = readonly [
    'readImagesInfinite',
    string,
    ImagesInfiniteParams['mode'],
    NormalModeFilters | ClassifierSamples | undefined,
    {
        metadata_values?: MetadataValues;
        text_embedding?: ReadImagesRequest['text_embedding'];
        query_expr?: QueryExpr;
    },
    ReadImagesRequest['sort_by']
];

export type SortExpr = SortFieldExpr | ({ source: 'evaluation_metric' } & EvaluationMetricSortExpr);
