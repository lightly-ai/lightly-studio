import type {
    ClassMetrics,
    EvaluationMetrics,
    EvaluationRunMetricsView,
    EvaluationRunView
} from '$lib/api/lightly_studio_local';

export type ComparableTaskType = 'object_detection' | 'instance_segmentation' | 'classification';
export type LeaderboardMetric =
    | 'map'
    | 'map50'
    | 'map75'
    | 'precision'
    | 'recall'
    | 'f1'
    | 'accuracy';
export type PerClassMetric = 'average_precision' | 'precision' | 'recall' | 'f1';
export type SelectionProblem = 'too_few_runs' | 'mixed_task_types' | 'unsupported_task_type';

export interface ComparedRun {
    run: EvaluationRunView;
    metrics: EvaluationRunMetricsView;
}

export interface ComparabilityReport {
    differentGroundTruth: boolean;
    differentImageSets: boolean;
    /** The IoU threshold or class matching differs. This changes precision, recall and F1. */
    differentMatchingConfig: boolean;
    staleRunIds: string[];
}

export interface PerClassRow {
    label: string;
    /** One value for each run, in the order of the runs. */
    values: (number | null)[];
    bestIndices: number[];
}

const COMPARABLE_TASK_TYPES: readonly string[] = [
    'object_detection',
    'instance_segmentation',
    'classification'
];
const MINIMUM_RUN_COUNT = 2;
const METRIC_DECIMALS = 3;
const MISSING_VALUE = '—';
const IOU_THRESHOLD_50 = '0.5';
const IOU_THRESHOLD_75 = '0.75';

export const LEADERBOARD_METRIC_LABELS: Record<LeaderboardMetric, string> = {
    map: 'mAP',
    map50: 'mAP@50',
    map75: 'mAP@75',
    precision: 'Precision',
    recall: 'Recall',
    f1: 'F1',
    accuracy: 'Accuracy'
};

export const SELECTION_PROBLEM_MESSAGES: Record<SelectionProblem, string> = {
    too_few_runs: 'Select at least two evaluation runs to compare.',
    mixed_task_types: 'Select runs of the same task type.',
    unsupported_task_type: 'Semantic segmentation runs have no metrics to compare.'
};

export const PER_CLASS_METRIC_LABELS: Record<PerClassMetric, string> = {
    average_precision: 'AP',
    precision: 'Precision',
    recall: 'Recall',
    f1: 'F1'
};

/** Metrics that need a run with average precision. */
export const AVERAGE_PRECISION_METRICS: readonly LeaderboardMetric[] = ['map', 'map50', 'map75'];

/** Metrics that depend on the IoU threshold and class matching of a run. */
export const MATCHING_DEPENDENT_METRICS: readonly LeaderboardMetric[] = [
    'precision',
    'recall',
    'f1'
];

export const formatMetricValue = (value: number | null): string =>
    value === null ? MISSING_VALUE : value.toFixed(METRIC_DECIMALS);

export const isComparableTaskType = (taskType: string): taskType is ComparableTaskType =>
    COMPARABLE_TASK_TYPES.includes(taskType);

export const validateSelection = (runs: EvaluationRunView[]): SelectionProblem | null => {
    if (runs.length < MINIMUM_RUN_COUNT) return 'too_few_runs';
    const taskTypes = new Set(runs.map((run) => run.task_type));
    if (taskTypes.size > 1) return 'mixed_task_types';
    if (!isComparableTaskType(runs[0].task_type)) return 'unsupported_task_type';
    return null;
};

export const leaderboardColumns = (taskType: ComparableTaskType): LeaderboardMetric[] => {
    switch (taskType) {
        case 'object_detection':
            return ['map', 'map50', 'map75', 'precision', 'recall', 'f1'];
        case 'instance_segmentation':
            return ['precision', 'recall', 'f1'];
        case 'classification':
            // Micro precision, recall and F1 equal accuracy with one label for each image.
            return ['accuracy'];
    }
};

export const perClassMetrics = (taskType: ComparableTaskType): PerClassMetric[] =>
    taskType === 'object_detection'
        ? ['average_precision', 'precision', 'recall', 'f1']
        : ['precision', 'recall', 'f1'];

export const leaderboardValue = (
    view: EvaluationRunMetricsView,
    metric: LeaderboardMetric
): number | null => {
    const { metrics } = view;
    switch (metric) {
        case 'map':
            return metrics.mean_average_precision ?? null;
        case 'map50':
            return mapAtThreshold(metrics, IOU_THRESHOLD_50);
        case 'map75':
            return mapAtThreshold(metrics, IOU_THRESHOLD_75);
        case 'accuracy':
            return metrics.accuracy;
        default:
            return metrics[metric];
    }
};

export const primaryMetric = (
    taskType: ComparableTaskType,
    runs: ComparedRun[]
): LeaderboardMetric => {
    if (taskType === 'classification') return 'accuracy';
    if (taskType === 'instance_segmentation') return 'f1';
    const anyRunHasMap = runs.some((entry) => leaderboardValue(entry.metrics, 'map') !== null);
    return anyRunHasMap ? 'map' : 'f1';
};

export const sortByPrimaryMetric = (
    runs: ComparedRun[],
    metric: LeaderboardMetric
): ComparedRun[] =>
    [...runs].sort((first, second) => {
        const firstValue = leaderboardValue(first.metrics, metric) ?? -Infinity;
        const secondValue = leaderboardValue(second.metrics, metric) ?? -Infinity;
        return secondValue - firstValue;
    });

export const compareRuns = (runs: ComparedRun[]): ComparabilityReport => ({
    differentGroundTruth: hasDifferentValues(runs.map((entry) => entry.run.gt_annotation_source)),
    differentImageSets: hasDifferentValues(
        runs.map((entry) => entry.metrics.evaluated_sample_set_hash)
    ),
    differentMatchingConfig:
        hasDifferentValues(runs.map((entry) => configValue(entry.run, 'iou_threshold'))) ||
        hasDifferentValues(runs.map((entry) => configValue(entry.run, 'classwise'))),
    staleRunIds: runs.filter((entry) => entry.run.stale_since !== null).map((entry) => entry.run.id)
});

export const perClassRows = (runs: ComparedRun[], metric: PerClassMetric): PerClassRow[] => {
    const classesByRun = runs.map(
        (entry) => new Map(entry.metrics.metrics.per_class.map((item) => [item.label, item]))
    );
    const labels = [...new Set(classesByRun.flatMap((classes) => [...classes.keys()]))].sort();
    return labels.map((label) => {
        const values = classesByRun.map((classes) => classValue(classes.get(label), metric));
        return { label, values, bestIndices: bestIndices(values) };
    });
};

export const bestIndices = (values: (number | null)[]): number[] => {
    const presentValues = values.filter((value): value is number => value !== null);
    if (presentValues.length === 0) return [];
    const best = Math.max(...presentValues);
    return values.flatMap((value, index) => (value === best ? [index] : []));
};

const mapAtThreshold = (metrics: EvaluationMetrics, threshold: string): number | null =>
    metrics.mean_average_precision_by_iou_threshold?.[threshold] ?? null;

const hasDifferentValues = (values: unknown[]): boolean => new Set(values).size > 1;

const configValue = (run: EvaluationRunView, key: string): unknown =>
    run.evaluation_run_configuration[key];

const classValue = (item: ClassMetrics | undefined, metric: PerClassMetric): number | null =>
    item === undefined ? null : (item[metric] ?? null);
