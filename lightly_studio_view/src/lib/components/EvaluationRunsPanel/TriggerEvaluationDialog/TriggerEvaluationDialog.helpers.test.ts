import { describe, expect, it } from 'vitest';
import { buildEvaluationRunBody, canSubmitEvaluation } from './TriggerEvaluationDialog.helpers';

describe('buildEvaluationRunBody', () => {
    const base = {
        gtSource: 'gt',
        predSource: 'pred',
        collectionId: 'collection-1',
        iouThreshold: 0.7,
        classwise: false
    };

    it('includes object-detection config for object_detection runs', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'object_detection' });

        expect(body).toEqual({
            task_type: 'object_detection',
            gt_annotation_source: 'gt',
            pred_annotation_source: 'pred',
            collection_id: 'collection-1',
            config: { iou_threshold: 0.7, classwise: false }
        });
    });

    it('omits config and filter for classification runs (full dataset)', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'classification' });

        expect(body).toEqual({
            task_type: 'classification',
            gt_annotation_source: 'gt',
            pred_annotation_source: 'pred',
            collection_id: 'collection-1'
        });
        expect('filter' in body).toBe(false);
    });

    it('omits config for semantic_segmentation runs', () => {
        const body = buildEvaluationRunBody({ ...base, taskType: 'semantic_segmentation' });

        expect(body.task_type).toBe('semantic_segmentation');
        expect('config' in body).toBe(false);
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
