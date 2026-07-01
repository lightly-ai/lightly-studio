import {
    createInfiniteQuery,
    infiniteQueryOptions,
    useQueryClient,
    type InfiniteData
} from '@tanstack/svelte-query';
import {
    listEvaluationMatches,
    type ConfusionCell,
    type EvaluationMatchesWithCountView,
    type EvaluationMatchSortField,
    type EvaluationMatchType,
    type ImageFilter,
    type SortDirection
} from '$lib/api/lightly_studio_local';
import { GRID_PAGE_SIZE } from '$lib/constants';

export interface EvaluationMatchesParams {
    datasetId: string;
    evaluationRunId: string;
    // Image collection used to scope the image-level filters.
    collectionId: string;
    matchTypes?: EvaluationMatchType[];
    annotationLabelIds?: string[];
    confusionCell?: ConfusionCell;
    imageFilter?: ImageFilter;
    sortField?: EvaluationMatchSortField;
    sortDirection?: SortDirection;
}

type MatchesQueryKey = [
    'listEvaluationMatchesInfinite',
    string,
    string,
    {
        collectionId: string;
        matchTypes?: EvaluationMatchType[];
        annotationLabelIds?: string[];
        confusionCell?: ConfusionCell;
        imageFilter?: ImageFilter;
        sortField?: EvaluationMatchSortField;
        sortDirection?: SortDirection;
    }
];

const createEvaluationMatchesInfiniteOptions = (params: EvaluationMatchesParams) => {
    const queryKey: MatchesQueryKey = [
        'listEvaluationMatchesInfinite',
        params.datasetId,
        params.evaluationRunId,
        {
            collectionId: params.collectionId,
            matchTypes: params.matchTypes,
            annotationLabelIds: params.annotationLabelIds,
            confusionCell: params.confusionCell,
            imageFilter: params.imageFilter,
            sortField: params.sortField,
            sortDirection: params.sortDirection
        }
    ];

    return infiniteQueryOptions<
        EvaluationMatchesWithCountView,
        Error,
        InfiniteData<EvaluationMatchesWithCountView>,
        MatchesQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const { data } = await listEvaluationMatches({
                path: {
                    dataset_id: params.datasetId,
                    evaluation_run_id: params.evaluationRunId
                },
                body: {
                    collection_id: params.collectionId,
                    match_types: params.matchTypes?.length ? params.matchTypes : undefined,
                    annotation_label_ids: params.annotationLabelIds?.length
                        ? params.annotationLabelIds
                        : undefined,
                    confusion_cell: params.confusionCell,
                    image_filter: params.imageFilter,
                    sort_field: params.sortField,
                    sort_direction: params.sortDirection,
                    pagination: { offset: pageParam, limit: GRID_PAGE_SIZE }
                },
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined
    });
};

export const useEvaluationMatchesInfinite = (getParams: () => EvaluationMatchesParams) => {
    const matches = createInfiniteQuery(() => createEvaluationMatchesInfiniteOptions(getParams()));
    const client = useQueryClient();

    const refresh = () => {
        const options = createEvaluationMatchesInfiniteOptions(getParams());
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return { matches, refresh };
};
