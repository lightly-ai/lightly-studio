import { derived, writable, type Readable } from 'svelte/store';
import {
    SortDirection,
    type AnnotationEvaluationMetricSortExpr,
    type EvaluationRunAnnotationMetricsInfoView
} from '$lib/api/lightly_studio_local';
import { usePostHog } from '$lib/hooks';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import { useAnnotationEvaluationMetricsInfo } from '$lib/hooks/useAnnotationEvaluationMetricsInfo/useAnnotationEvaluationMetricsInfo';
import { formatEvaluationMetricLabel } from '$lib/hooks/useSortFields/useSortFields.svelte';

export interface AnnotationSortField {
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
    selectedLabel: Readable<string | null>;
    isFieldSelected: Readable<(field: AnnotationSortField) => boolean>;
    handleFieldClick: (field: AnnotationSortField) => void;
    clearSort: () => void;
    toggleDirection: () => void;
    /** Dispose internal reactive effects. Call on cleanup to prevent leaks. */
    dispose: () => void;
}

export function mapRunsToAnnotationSortFields(
    runs: EvaluationRunAnnotationMetricsInfoView[]
): AnnotationSortField[] {
    return runs.flatMap((run) =>
        run.metric_names.map(
            (metricName): AnnotationSortField => ({
                source: 'annotation_evaluation_metric',
                evaluation_run_id: run.run_id,
                metric_name: metricName,
                label: formatEvaluationMetricLabel(run.run_name, metricName)
            })
        )
    );
}

export function useAnnotationOrderBy({
    collectionId
}: UseAnnotationOrderByParams): UseAnnotationOrderByReturn {
    const { sortByFor, getSortBy, setSortBy } = useAnnotationSortBy();
    const { trackEvent } = usePostHog();
    const metricsInfo = useAnnotationEvaluationMetricsInfo({ collectionId });

    // In TanStack v6, query results are reactive objects, not Svelte stores. Bridge to a
    // writable store via $effect.root so it integrates with derived(). $effect.root is used
    // instead of $effect because this hook may be called outside a component context.
    const allSortFields = writable<AnnotationSortField[]>([]);
    const disposeEffect = $effect.root(() => {
        $effect(() => {
            void metricsInfo.dataUpdatedAt;
            allSortFields.set(mapRunsToAnnotationSortFields(metricsInfo.data ?? []));
        });
    });

    const current = derived(sortByFor, ($sortByFor) => $sortByFor(collectionId()));

    const selectedDirection = derived(
        current,
        ($current) => $current?.direction ?? SortDirection.ASC
    );

    const selectedLabel = derived([current, allSortFields], ([$current, $allSortFields]) => {
        if (!$current) return null;
        return (
            $allSortFields.find((field) => isSameField(field, $current))?.label ??
            $current.metric_name
        );
    });

    // Returns a checker function so the template can call $isFieldSelected(field) and
    // reactively update when the selection changes.
    const isFieldSelected = derived(
        current,
        ($current) =>
            (field: AnnotationSortField): boolean =>
                $current !== null && isSameField(field, $current)
    );

    function applySort(expr: AnnotationEvaluationMetricSortExpr) {
        setSortBy(collectionId(), expr);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source: 'annotation_evaluation_metric',
            field_name: expr.metric_name,
            direction: expr.direction
        });
    }

    function handleFieldClick(field: AnnotationSortField) {
        const existing = getSortBy(collectionId());
        if (existing && isSameField(field, existing)) {
            clearSort();
            return;
        }
        applySort({
            source: 'annotation_evaluation_metric',
            evaluation_run_id: field.evaluation_run_id,
            metric_name: field.metric_name,
            direction: existing?.direction ?? SortDirection.ASC
        });
    }

    function clearSort() {
        setSortBy(collectionId(), null);
    }

    function toggleDirection() {
        const existing = getSortBy(collectionId());
        if (!existing) return;
        applySort({
            ...existing,
            direction:
                existing.direction === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC
        });
    }

    return {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        clearSort,
        toggleDirection,
        dispose: disposeEffect
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
