import { derived, get, type Readable } from 'svelte/store';
import { SortDirection } from '$lib/api/lightly_studio_local';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { usePostHog } from '$lib/hooks';
import {
    formatEvaluationMetricLabel,
    useSortFields,
    type ImageSortField,
    type SortField
} from '$lib/hooks/useSortFields/useSortFields.svelte';
import type { SortExpr } from '$lib/hooks/useImagesInfinite/types';

interface UseOrderByParams {
    collectionId: () => string;
    datasetId: () => string;
}

interface UseOrderByReturn {
    allSortFields: Readable<SortField[]>;
    selectedDirection: Readable<SortDirection>;
    selectedLabel: Readable<string | null>;
    isFieldSelected: Readable<(field: SortField) => boolean>;
    handleFieldClick: (field: SortField) => void;
    toggleDirection: () => void;
    /** Dispose internal reactive effects. Call on cleanup to prevent leaks. */
    dispose: () => void;
}

function checkIsFieldSelected(field: SortField, current: SortExpr | undefined): boolean {
    if (!current) return false;
    if (field.source === 'evaluation_metric') {
        return (
            current.source === 'evaluation_metric' &&
            current.evaluation_run_name === field.evaluation_run_name &&
            current.metric_name === field.metric_name
        );
    }
    return (
        current.source !== 'evaluation_metric' &&
        current.field_name === field.value &&
        current.source === field.source
    );
}

function sortExprAnalytics(expr: SortExpr): { sort_source: string; field_name: string } {
    if (expr.source === 'evaluation_metric') {
        return {
            sort_source: 'evaluation_metric',
            field_name: `${expr.evaluation_run_name}.${expr.metric_name}`
        };
    }
    return {
        sort_source: expr.source === 'metadata' ? 'metadata_field' : 'image_field',
        field_name: expr.field_name
    };
}

export function useOrderBy({ collectionId, datasetId }: UseOrderByParams): UseOrderByReturn {
    const { imageSortBy, updateSortBy } = useImageFilters();
    const { allSortFields, dispose } = useSortFields({ datasetId });
    const { trackEvent } = usePostHog();

    const selectedDirection = derived(
        imageSortBy,
        ($imageSortBy) => $imageSortBy?.[0]?.direction ?? SortDirection.ASC
    );

    const selectedLabel = derived(
        [imageSortBy, allSortFields],
        ([$imageSortBy, $allSortFields]) => {
            const current = $imageSortBy?.[0];
            if (!current) return null;
            if (current.source === 'evaluation_metric') {
                return (
                    $allSortFields.find(
                        (field) =>
                            field.source === 'evaluation_metric' &&
                            field.evaluation_run_name === current.evaluation_run_name &&
                            field.metric_name === current.metric_name
                    )?.label ??
                    formatEvaluationMetricLabel(current.evaluation_run_name, current.metric_name)
                );
            }
            return (
                $allSortFields
                    .filter((f): f is ImageSortField => f.source !== 'evaluation_metric')
                    .find((f) => f.source === current.source && f.value === current.field_name)
                    ?.label ?? null
            );
        }
    );

    // Returns a checker function so the template can call $isFieldSelected(field)
    // and reactively update when imageSortBy changes.
    const isFieldSelected = derived(
        imageSortBy,
        ($imageSortBy) =>
            (field: SortField): boolean =>
                checkIsFieldSelected(field, $imageSortBy?.[0])
    );

    function handleFieldClick(field: SortField) {
        const current = get(imageSortBy)?.[0];
        if (checkIsFieldSelected(field, current)) {
            updateSortBy(null);
            return;
        }
        const direction = get(selectedDirection);
        const next: SortExpr =
            field.source === 'evaluation_metric'
                ? {
                      source: 'evaluation_metric',
                      evaluation_run_name: field.evaluation_run_name,
                      metric_name: field.metric_name,
                      direction
                  }
                : {
                      source: field.source,
                      field_name: field.value,
                      direction,
                      is_numeric: field.is_numeric ?? false
                  };
        updateSortBy([next]);
        const { sort_source, field_name } = sortExprAnalytics(next);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source,
            field_name,
            direction
        });
    }

    function toggleDirection() {
        const current = get(imageSortBy)?.[0];
        if (!current) return;
        const direction =
            get(selectedDirection) === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC;
        const next: SortExpr = { ...current, direction };
        updateSortBy([next]);
        const { sort_source, field_name } = sortExprAnalytics(next);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source,
            field_name,
            direction
        });
    }

    return {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection,
        dispose
    };
}
