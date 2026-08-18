import { derived, get, writable, type Readable, type Writable } from 'svelte/store';
import {
    SortDirection,
    type AnnotationEvaluationMetricSortExpr,
    type EvaluationRunAnnotationMetricsInfoView
} from '$lib/api/lightly_studio_local';
import {
    formatEvaluationMetricLabel,
    useAnnotationEvaluationMetricsInfo,
    useAnnotationSortBy,
    usePostHog
} from '$lib/hooks';

interface AnnotationSortField {
    source: 'annotation_evaluation_metric';
    evaluation_run_id: string;
    metric_name: string;
    label: string;
}

interface UseAnnotationOrderByParams {
    collectionId: () => string;
}

interface UseAnnotationOrderByReturn {
    allSortFields: Readable<AnnotationSortField[]>;
    selectedDirection: Readable<SortDirection>;
    /** Index of the selected field in `allSortFields`, -1 when nothing is selected. */
    selectedIndex: Readable<number>;
    handleFieldClick: (field: AnnotationSortField) => void;
    toggleDirection: () => void;
    /** Dispose internal reactive effects. Call on cleanup to prevent leaks. */
    dispose: () => void;
}

export function mapRunsToAnnotationSortFields(
    runs: EvaluationRunAnnotationMetricsInfoView[]
): AnnotationSortField[] {
    return runs.flatMap((run) =>
        run.metrics.map(
            (metric): AnnotationSortField => ({
                source: 'annotation_evaluation_metric',
                evaluation_run_id: run.run_id,
                metric_name: metric.metric_name,
                label: formatEvaluationMetricLabel(run.run_name, metric.metric_name)
            })
        )
    );
}

interface QueryBridge {
    allSortFields: Readable<AnnotationSortField[]>;
    currentCollectionId: Readable<string>;
    dispose: () => void;
}

/**
 * Bridges the runes-based query result and the collection getter into stores. In TanStack v6,
 * query results are reactive objects, not Svelte stores, and the getter is only tracked inside
 * an effect. `$effect.root` is used instead of `$effect` because this hook may be called outside
 * a component context.
 */
function bridgeToStores(collectionId: () => string): QueryBridge {
    const allSortFields: Writable<AnnotationSortField[]> = writable([]);
    const currentCollectionId: Writable<string> = writable(collectionId());
    const metricsInfo = useAnnotationEvaluationMetricsInfo({ collectionId });

    const dispose = $effect.root(() => {
        $effect(() => {
            currentCollectionId.set(collectionId());
        });
        $effect(() => {
            void metricsInfo.dataUpdatedAt;
            allSortFields.set(mapRunsToAnnotationSortFields(metricsInfo.data ?? []));
        });
    });

    return { allSortFields, currentCollectionId, dispose };
}

interface SortActions {
    handleFieldClick: (field: AnnotationSortField) => void;
    toggleDirection: () => void;
}

function createSortActions(
    collectionId: () => string,
    allSortFields: Readable<AnnotationSortField[]>
): SortActions {
    const { getSortBy, setSortBy } = useAnnotationSortBy();
    const { trackEvent } = usePostHog();

    function applySort(expr: AnnotationEvaluationMetricSortExpr): void {
        setSortBy(collectionId(), expr);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source: 'annotation_evaluation_metric',
            field_name: analyticsFieldName(get(allSortFields), expr),
            direction: expr.direction
        });
    }

    function handleFieldClick(field: AnnotationSortField): void {
        const existing = getSortBy(collectionId());
        if (existing && isSameField(field, existing)) {
            setSortBy(collectionId(), null);
            return;
        }
        applySort({
            source: 'annotation_evaluation_metric',
            evaluation_run_id: field.evaluation_run_id,
            metric_name: field.metric_name,
            direction: existing?.direction ?? SortDirection.ASC
        });
    }

    function toggleDirection(): void {
        const existing = getSortBy(collectionId());
        if (!existing) return;
        applySort({
            ...existing,
            direction:
                existing.direction === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC
        });
    }

    return { handleFieldClick, toggleDirection };
}

export function useAnnotationOrderBy({
    collectionId
}: UseAnnotationOrderByParams): UseAnnotationOrderByReturn {
    const { sortByFor } = useAnnotationSortBy();
    const { allSortFields, currentCollectionId, dispose } = bridgeToStores(collectionId);

    const current = derived(
        [sortByFor, currentCollectionId],
        ([$sortByFor, $currentCollectionId]) => $sortByFor($currentCollectionId)
    );

    const selectedDirection = derived(
        current,
        ($current) => $current?.direction ?? SortDirection.ASC
    );

    const selectedIndex = derived([current, allSortFields], ([$current, $allSortFields]) =>
        $current ? $allSortFields.findIndex((field) => isSameField(field, $current)) : -1
    );

    return {
        allSortFields,
        selectedDirection,
        selectedIndex,
        ...createSortActions(collectionId, allSortFields),
        dispose
    };
}

function isSameField(
    field: AnnotationSortField,
    expr: AnnotationEvaluationMetricSortExpr
): boolean {
    return (
        field.evaluation_run_id === expr.evaluation_run_id && field.metric_name === expr.metric_name
    );
}

/** Names the run alongside the metric, so analytics can tell two runs of one metric apart. */
function analyticsFieldName(
    fields: AnnotationSortField[],
    expr: AnnotationEvaluationMetricSortExpr
): string {
    const field = fields.find((candidate) => isSameField(candidate, expr));
    return field?.label ?? formatEvaluationMetricLabel(expr.evaluation_run_id, expr.metric_name);
}
