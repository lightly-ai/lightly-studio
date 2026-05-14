import { derived, get } from 'svelte/store';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useEvaluationSampleMetricsInfo } from '$lib/hooks/useEvaluationSampleMetricsInfo/useEvaluationSampleMetricsInfo';
import type { SortExpr } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

type ImageSortField = {
    source: SortFieldExpr['source'];
    value: string;
    label: string;
    is_numeric?: boolean;
};

type EvalSortField = {
    source: 'evaluation_metric';
    evaluation_run_name: string;
    metric_name: string;
    label: string;
};

export type SortField = ImageSortField | EvalSortField;

const IMAGE_SORT_FIELDS: ImageSortField[] = [
    { source: 'image', value: 'file_name', label: 'file name' },
    { source: 'image', value: 'file_path_abs', label: 'file path' },
    { source: 'image', value: 'created_at', label: 'created at' },
    { source: 'image', value: 'width', label: 'width' },
    { source: 'image', value: 'height', label: 'height' }
];

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
    const { metadataInfo } = useMetadataFilters();
    const metricsInfo = useEvaluationSampleMetricsInfo({ datasetId });

    const metadataSortFields = derived(metadataInfo, ($metadataInfo) =>
        ($metadataInfo ?? [])
            .filter((info) => ['integer', 'float', 'string', 'boolean'].includes(info.type))
            .map(
                (info): ImageSortField => ({
                    source: 'metadata' as SortFieldExpr['source'],
                    value: info.name,
                    label: `metadata.${info.name}`,
                    is_numeric: info.type === 'integer' || info.type === 'float'
                })
            )
    );

    const evalSortFields = derived(metricsInfo, ($metricsInfo) =>
        ($metricsInfo.data ?? []).flatMap((run) =>
            run.metrics.map(
                (metric): EvalSortField => ({
                    source: 'evaluation_metric',
                    evaluation_run_name: run.run_name,
                    metric_name: metric.metric_name,
                    label: `${run.run_name}_${metric.metric_name}`
                })
            )
        )
    );

    const allSortFields = derived(
        [metadataSortFields, evalSortFields],
        ([$metadataSortFields, $evalSortFields]) => [
            ...IMAGE_SORT_FIELDS,
            ...$metadataSortFields,
            ...$evalSortFields
        ]
    );

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
