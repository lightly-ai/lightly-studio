import { describe, expect, it } from 'vitest';
import type {
    ClassMetrics,
    EvaluationRunMetricsView,
    EvaluationRunView
} from '$lib/api/lightly_studio_local';
import {
    bestIndices,
    compareRuns,
    leaderboardColumns,
    leaderboardValue,
    perClassMetrics,
    perClassRows,
    primaryMetric,
    sortByPrimaryMetric,
    validateSelection,
    type ComparedRun
} from './EvaluationComparison.helpers';

const makeRun = (overrides: Partial<EvaluationRunView> = {}): EvaluationRunView => ({
    id: 'run-1',
    name: 'run 1',
    task_type: 'object_detection',
    evaluation_run_configuration: { iou_threshold: 0.5, classwise: true },
    created_at: new Date('2026-01-01T00:00:00Z'),
    stale_since: null,
    gt_annotation_source: 'gt',
    pred_annotation_source: 'pred',
    ...overrides
});

const makeClass = (label: string, averagePrecision: number | null): ClassMetrics => ({
    label,
    precision: 0.5,
    recall: 0.5,
    f1: 0.5,
    support: 1,
    average_precision: averagePrecision
});

const makeMetrics = (
    overrides: Partial<EvaluationRunMetricsView['metrics']> = {},
    sampleSetHash = 'hash-a'
): EvaluationRunMetricsView => ({
    evaluation_run_id: 'run-1',
    evaluated_sample_count: 2,
    evaluated_sample_set_hash: sampleSetHash,
    metrics: {
        per_class: [],
        precision: 0.6,
        recall: 0.7,
        f1: 0.65,
        accuracy: null,
        mean_average_precision: 0.4,
        mean_average_precision_by_iou_threshold: { '0.5': 0.8, '0.75': 0.3 },
        ...overrides
    }
});

const compared = (
    id: string,
    runOverrides: Partial<EvaluationRunView> = {},
    metrics: EvaluationRunMetricsView = makeMetrics()
): ComparedRun => ({ run: makeRun({ id, name: id, ...runOverrides }), metrics });

describe('validateSelection', () => {
    it('needs at least two runs', () => {
        expect(validateSelection([])).toBe('too_few_runs');
        expect(validateSelection([makeRun()])).toBe('too_few_runs');
    });

    it('rejects runs of different task types', () => {
        expect(
            validateSelection([makeRun(), makeRun({ id: 'run-2', task_type: 'classification' })])
        ).toBe('mixed_task_types');
    });

    it('rejects semantic segmentation runs', () => {
        const semantic = makeRun({ task_type: 'semantic_segmentation' });
        expect(validateSelection([semantic, { ...semantic, id: 'run-2' }])).toBe(
            'unsupported_task_type'
        );
    });

    it('accepts two runs of a comparable task type', () => {
        expect(validateSelection([makeRun(), makeRun({ id: 'run-2' })])).toBeNull();
    });
});

describe('leaderboardColumns', () => {
    it.each([
        ['object_detection', ['map', 'map50', 'map75', 'precision', 'recall', 'f1']],
        ['instance_segmentation', ['precision', 'recall', 'f1']],
        ['classification', ['accuracy']]
    ] as const)('returns the columns for %s', (taskType, columns) => {
        expect(leaderboardColumns(taskType)).toEqual(columns);
    });
});

describe('perClassMetrics', () => {
    it('puts average precision first for object detection only', () => {
        expect(perClassMetrics('object_detection')).toEqual([
            'average_precision',
            'precision',
            'recall',
            'f1'
        ]);
        expect(perClassMetrics('classification')).toEqual(['precision', 'recall', 'f1']);
    });
});

describe('leaderboardValue', () => {
    it('reads mAP at the 0.5 and 0.75 IoU thresholds', () => {
        const metrics = makeMetrics();
        expect(leaderboardValue(metrics, 'map')).toBe(0.4);
        expect(leaderboardValue(metrics, 'map50')).toBe(0.8);
        expect(leaderboardValue(metrics, 'map75')).toBe(0.3);
        expect(leaderboardValue(metrics, 'f1')).toBe(0.65);
    });

    it('returns null for a run without average precision', () => {
        const metrics = makeMetrics({
            mean_average_precision: null,
            mean_average_precision_by_iou_threshold: null
        });
        expect(leaderboardValue(metrics, 'map')).toBeNull();
        expect(leaderboardValue(metrics, 'map50')).toBeNull();
        expect(leaderboardValue(metrics, 'accuracy')).toBeNull();
    });
});

describe('primaryMetric', () => {
    const withoutAveragePrecision = makeMetrics({ mean_average_precision: null });

    it('ranks object detection by mAP when a run has it', () => {
        const runs = [compared('a', {}, withoutAveragePrecision), compared('b')];
        expect(primaryMetric('object_detection', runs)).toBe('map');
    });

    it('ranks object detection by F1 when no run has mAP', () => {
        const runs = [compared('a', {}, withoutAveragePrecision)];
        expect(primaryMetric('object_detection', runs)).toBe('f1');
    });

    it('ranks instance segmentation by F1 and classification by accuracy', () => {
        expect(primaryMetric('instance_segmentation', [])).toBe('f1');
        expect(primaryMetric('classification', [])).toBe('accuracy');
    });
});

describe('sortByPrimaryMetric', () => {
    it('sorts descending and puts missing values last', () => {
        const low = compared('low', {}, makeMetrics({ mean_average_precision: 0.2 }));
        const missing = compared('missing', {}, makeMetrics({ mean_average_precision: null }));
        const high = compared('high', {}, makeMetrics({ mean_average_precision: 0.9 }));

        const sorted = sortByPrimaryMetric([low, missing, high], 'map');

        expect(sorted.map((entry) => entry.run.id)).toEqual(['high', 'low', 'missing']);
    });
});

describe('compareRuns', () => {
    it('reports nothing for runs with the same setup', () => {
        expect(compareRuns([compared('a'), compared('b')])).toEqual({
            differentGroundTruth: false,
            differentImageSets: false,
            differentMatchingConfig: false,
            staleRunIds: []
        });
    });

    it('reports a different ground truth source', () => {
        const report = compareRuns([
            compared('a'),
            compared('b', { gt_annotation_source: 'gt_v2' })
        ]);
        expect(report.differentGroundTruth).toBe(true);
    });

    it('reports different evaluated images', () => {
        const report = compareRuns([compared('a'), compared('b', {}, makeMetrics({}, 'hash-b'))]);
        expect(report.differentImageSets).toBe(true);
    });

    it.each([
        [{ iou_threshold: 0.7, classwise: true }],
        [{ iou_threshold: 0.5, classwise: false }]
    ])('reports different matching settings %o', (configuration) => {
        const report = compareRuns([
            compared('a'),
            compared('b', { evaluation_run_configuration: configuration })
        ]);
        expect(report.differentMatchingConfig).toBe(true);
    });

    it('lists stale runs', () => {
        const report = compareRuns([
            compared('a'),
            compared('b', { stale_since: new Date('2026-01-02T00:00:00Z') })
        ]);
        expect(report.staleRunIds).toEqual(['b']);
    });
});

describe('perClassRows', () => {
    it('uses the union of labels and null for a class that a run does not have', () => {
        const runA = compared(
            'a',
            {},
            makeMetrics({ per_class: [makeClass('cat', 0.9), makeClass('dog', 0.4)] })
        );
        const runB = compared('b', {}, makeMetrics({ per_class: [makeClass('cat', 0.7)] }));

        expect(perClassRows([runA, runB], 'average_precision')).toEqual([
            { label: 'cat', values: [0.9, 0.7], bestIndices: [0] },
            { label: 'dog', values: [0.4, null], bestIndices: [0] }
        ]);
    });

    it('returns null for a missing average precision', () => {
        const run = compared('a', {}, makeMetrics({ per_class: [makeClass('cat', null)] }));

        expect(perClassRows([run], 'average_precision')).toEqual([
            { label: 'cat', values: [null], bestIndices: [] }
        ]);
    });
});

describe('bestIndices', () => {
    it('returns every index that ties for the best value', () => {
        expect(bestIndices([0.5, null, 0.5, 0.2])).toEqual([0, 2]);
    });

    it('returns no index when every value is missing', () => {
        expect(bestIndices([null, null])).toEqual([]);
    });
});
