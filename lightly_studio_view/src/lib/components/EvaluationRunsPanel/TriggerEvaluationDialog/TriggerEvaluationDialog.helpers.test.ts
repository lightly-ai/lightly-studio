import { describe, expect, it } from 'vitest';
import {
    buildEvaluationRunBody,
    canSubmitEvaluation,
    defaultEvaluationRunName,
    sourceMatchesTask
} from './TriggerEvaluationDialog.helpers';

describe('buildEvaluationRunBody', () => {
    const now = new Date(2026, 5, 24, 10, 15, 33); // local time
    const base = {
        gtSource: 'gt',
        predSource: 'pred',
        collectionId: 'collection-1',
        iouThreshold: 0.7,
        classwise: false,
        now
    };

    it('includes object-detection config and a local-time name for object_detection runs', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'object_detection' });

        expect(body).toEqual({
            task_type: 'object_detection',
            gt_annotation_source: 'gt',
            pred_annotation_source: 'pred',
            collection_id: 'collection-1',
            name: 'object_detection 2026-06-24 10:15:33',
            config: { iou_threshold: 0.7, classwise: false }
        });
    });

    it('omits config and filter for classification runs (full dataset)', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'classification' });

        expect(body).toEqual({
            task_type: 'classification',
            gt_annotation_source: 'gt',
            pred_annotation_source: 'pred',
            collection_id: 'collection-1',
            name: 'classification 2026-06-24 10:15:33'
        });
        expect('filter' in body).toBe(false);
    });

    it('omits config for semantic_segmentation runs', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'semantic_segmentation' });

        expect(body.task_type).toBe('semantic_segmentation');
        expect('config' in body).toBe(false);
    });

    it('uses a provided name over the default, trimming whitespace', () => {
        const body = buildEvaluationRunBody({
            ...base,
            taskType: 'object_detection',
            name: '  my run  '
        });
        expect(body.name).toBe('my run');
    });

    it('falls back to the default name when the provided name is blank', () => {
        const body = buildEvaluationRunBody({
            ...base,
            taskType: 'object_detection',
            name: '   '
        });
        expect(body.name).toBe('object_detection 2026-06-24 10:15:33');
    });
});

describe('defaultEvaluationRunName', () => {
    it('formats the task type and local time, zero-padded', () => {
        const name = defaultEvaluationRunName('object_detection', new Date(2026, 0, 5, 9, 3, 7));
        expect(name).toBe('object_detection 2026-01-05 09:03:07');
    });
});

describe('canSubmitEvaluation', () => {
    it('allows submit when both sources differ and not submitting', () => {
        expect(
            canSubmitEvaluation({ gtSource: 'gt', predSource: 'pred', isSubmitting: false })
        ).toBe(true);
    });

    it('blocks submit when a source is missing, sources match, or a request is in flight', () => {
        expect(
            canSubmitEvaluation({ gtSource: undefined, predSource: 'pred', isSubmitting: false })
        ).toBe(false);
        expect(canSubmitEvaluation({ gtSource: 'gt', predSource: 'gt', isSubmitting: false })).toBe(
            false
        );
        expect(
            canSubmitEvaluation({ gtSource: 'gt', predSource: 'pred', isSubmitting: true })
        ).toBe(false);
    });
});

describe('sourceMatchesTask', () => {
    it('matches a source whose annotations are all the task type', () => {
        expect(sourceMatchesTask(['object_detection'], 'object_detection')).toBe(true);
        expect(sourceMatchesTask(['classification'], 'classification')).toBe(true);
        expect(sourceMatchesTask(['segmentation_mask'], 'semantic_segmentation')).toBe(true);
    });

    it('rejects empty, mismatched, or mixed-type sources', () => {
        expect(sourceMatchesTask([], 'object_detection')).toBe(false);
        expect(sourceMatchesTask(['classification'], 'object_detection')).toBe(false);
        expect(sourceMatchesTask(['object_detection', 'classification'], 'object_detection')).toBe(
            false
        );
    });
});
