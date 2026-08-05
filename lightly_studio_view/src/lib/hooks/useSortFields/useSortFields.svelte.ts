import { derived, writable, type Readable } from 'svelte/store';
import type { SortFieldExpr, EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local';
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
    /** When `video`, only metadata fields are exposed (no image/eval fields). */
    mediaType?: 'image' | 'video';
}

interface UseSortFieldsReturn {
    allSortFields: Readable<SortField[]>;
    /** Dispose the detached $effect.root. Call on cleanup to prevent leaks. */
    dispose: () => void;
}

export const IMAGE_SORT_FIELDS: ImageSortField[] = [
    { source: 'image', value: 'file_name', label: 'file name' },
    { source: 'image', value: 'file_path_abs', label: 'file path' },
    { source: 'image', value: 'created_at', label: 'created at' },
    { source: 'image', value: 'width', label: 'width' },
    { source: 'image', value: 'height', label: 'height' }
];

/** Always-available video triage sort (also appears via metadata info when present). */
export const VIDEO_CAPTION_QUALITY_SORT_FIELDS: ImageSortField[] = [
    {
        source: 'metadata',
        value: 'min_caption_segment_match_score',
        label: 'min caption match',
        is_numeric: true
    },
    {
        source: 'metadata',
        value: 'avg_caption_segment_match_score',
        label: 'avg caption match',
        is_numeric: true
    }
];

export function formatEvaluationMetricLabel(evaluationRunName: string, metricName: string): string {
    return `${evaluationRunName}.${metricName}`;
}

function mapRunsToEvalFields(runs: EvaluationRunMetricsInfoView[]): EvalSortField[] {
    return runs.flatMap((run) =>
        run.metrics.map(
            (metric): EvalSortField => ({
                source: 'evaluation_metric',
                evaluation_run_name: run.run_name,
                metric_name: metric.metric_name,
                label: formatEvaluationMetricLabel(run.run_name, metric.metric_name)
            })
        )
    );
}

export function useSortFields({
    datasetId,
    mediaType = 'image'
}: UseSortFieldsParams): UseSortFieldsReturn {
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

    // In TanStack v6, query results are reactive objects, not Svelte stores.
    // Bridge to a writable store via $effect.root so it integrates with derived().
    // $effect.root is used instead of $effect because this hook may be called
    // outside a component context (e.g. in tests).
    const evalSortFields = writable<EvalSortField[]>([]);
    const disposeEffect = $effect.root(() => {
        $effect(() => {
            void metricsInfo.dataUpdatedAt;
            evalSortFields.set(mapRunsToEvalFields(metricsInfo.data ?? []));
        });
    });

    const allSortFields = derived(
        [metadataSortFields, evalSortFields],
        ([$metadataSortFields, $evalSortFields]) => {
            if (mediaType === 'video') {
                const metadataNames = new Set($metadataSortFields.map((field) => field.value));
                const captionFields = VIDEO_CAPTION_QUALITY_SORT_FIELDS.filter(
                    (field) => !metadataNames.has(field.value)
                );
                return [...captionFields, ...$metadataSortFields];
            }
            return [...IMAGE_SORT_FIELDS, ...$metadataSortFields, ...$evalSortFields];
        }
    );

    return { allSortFields, dispose: disposeEffect };
}
