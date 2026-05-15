import { derived, get } from 'svelte/store';
import { SortDirection } from '$lib/api/lightly_studio_local';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useSortFields } from '$lib/hooks/useSortFields/useSortFields';
import type { ImageSortField, SortField } from '$lib/hooks/useSortFields/useSortFields';
import type { SortExpr } from '../useImagesInfinite/types';

export type { SortField } from '$lib/hooks/useSortFields/useSortFields';

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

export function useOrderBy({ datasetId }: { datasetId: string }) {
    const { imageSortBy, updateSortBy } = useImageFilters();
    const { allSortFields } = useSortFields({ datasetId });

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
                return `${current.evaluation_run_name}_${current.metric_name}`;
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
        } else if (field.source === 'evaluation_metric') {
            updateSortBy([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: field.evaluation_run_name,
                    metric_name: field.metric_name,
                    direction: get(selectedDirection)
                }
            ]);
        } else {
            updateSortBy([
                {
                    source: field.source,
                    field_name: field.value,
                    direction: get(selectedDirection),
                    is_numeric: field.is_numeric ?? false
                }
            ]);
        }
    }

    function toggleDirection() {
        const current = get(imageSortBy)?.[0];
        if (!current) return;
        const next =
            get(selectedDirection) === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC;
        if (current.source === 'evaluation_metric') {
            updateSortBy([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: current.evaluation_run_name,
                    metric_name: current.metric_name,
                    direction: next
                }
            ]);
        } else {
            updateSortBy([
                {
                    source: current.source,
                    field_name: current.field_name,
                    direction: next,
                    is_numeric: current.is_numeric
                }
            ]);
        }
    }

    return {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection
    };
}
