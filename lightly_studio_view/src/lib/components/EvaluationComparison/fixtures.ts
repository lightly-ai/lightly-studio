import type {
    ClassMetrics,
    EvaluationMetrics,
    EvaluationRunMetricsView,
    EvaluationRunView
} from '$lib/api/lightly_studio_local';
import type { ComparedRun } from './EvaluationComparison.helpers';

export const makeRun = (overrides: Partial<EvaluationRunView> = {}): EvaluationRunView => ({
    id: 'run-1',
    name: 'run 1',
    task_type: 'object_detection',
    evaluation_run_configuration: { iou_threshold: 0.5, classwise: true },
    created_at: new Date('2026-01-01T00:00:00Z'),
    stale_since: null,
    gt_annotation_source: 'ground_truth',
    pred_annotation_source: 'predictions',
    ...overrides
});

export const makeClassMetrics = (label: string, averagePrecision: number | null): ClassMetrics => ({
    label,
    precision: 0.5,
    recall: 0.5,
    f1: 0.5,
    support: 1,
    average_precision: averagePrecision
});

export const makeComparedRun = (
    id: string,
    metrics: Partial<EvaluationMetrics> = {},
    runOverrides: Partial<EvaluationRunView> = {}
): ComparedRun => ({
    run: makeRun({ id, name: id, ...runOverrides }),
    metrics: makeMetricsView(id, metrics)
});

export const makeMetricsView = (
    runId: string,
    metrics: Partial<EvaluationMetrics> = {}
): EvaluationRunMetricsView => ({
    evaluation_run_id: runId,
    evaluated_sample_count: 2,
    evaluated_sample_set_hash: 'hash-a',
    metrics: {
        per_class: [makeClassMetrics('cat', 0.5)],
        precision: 0.6,
        recall: 0.7,
        f1: 0.65,
        accuracy: null,
        mean_average_precision: 0.4,
        mean_average_precision_by_iou_threshold: { '0.5': 0.8, '0.75': 0.3 },
        ...metrics
    }
});
