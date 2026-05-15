import { derived, type Readable } from 'svelte/store';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useEvaluationSampleMetricsInfo } from '$lib/hooks/useEvaluationSampleMetricsInfo/useEvaluationSampleMetricsInfo';

export interface ImageSortField {
    source: SortFieldExpr['source'];
    value: string;
    label: string;
    is_numeric?: boolean;
}

export interface EvalSortField {
    source: 'evaluation_metric';
    evaluation_run_name: string;
    metric_name: string;
    label: string;
}

export type SortField = ImageSortField | EvalSortField;

interface UseSortFieldsParams {
    datasetId: string;
}

interface UseSortFieldsReturn {
    allSortFields: Readable<SortField[]>;
}

export const IMAGE_SORT_FIELDS: ImageSortField[] = [
    { source: 'image', value: 'file_name', label: 'file name' },
    { source: 'image', value: 'file_path_abs', label: 'file path' },
    { source: 'image', value: 'created_at', label: 'created at' },
    { source: 'image', value: 'width', label: 'width' },
    { source: 'image', value: 'height', label: 'height' }
];

export function useSortFields({ datasetId }: UseSortFieldsParams): UseSortFieldsReturn {
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

    return { allSortFields };
}
