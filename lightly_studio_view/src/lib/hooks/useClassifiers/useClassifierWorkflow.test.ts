import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useClassifierWorkflow } from './useClassifierWorkflow';

describe('useClassifierWorkflow', () => {
    const classifierWorkflow = useClassifierWorkflow();

    beforeEach(() => classifierWorkflow.close());

    it('transitions from creation to refinement without closing', () => {
        classifierWorkflow.openCreate();
        expect(get(classifierWorkflow.isOpen)).toBe(true);

        classifierWorkflow.setTemporaryClassifier('classifier-id', 'Zebras', [
            'positive',
            'negative'
        ]);
        expect(get(classifierWorkflow.workflow).phase).toBe('create');

        classifierWorkflow.openRefine('temp', 'classifier-id', 'Zebras', ['positive', 'negative']);

        expect(get(classifierWorkflow.workflow)).toMatchObject({
            phase: 'refine',
            mode: 'temp',
            classifierId: 'classifier-id'
        });
        expect(get(classifierWorkflow.isOpen)).toBe(true);
    });

    it('aggregates agreement using sample counts and keeps the latest round', () => {
        classifierWorkflow.openRefine('existing', 'classifier-id', 'Zebras', [
            'positive',
            'negative'
        ]);
        classifierWorkflow.recordReview(18, 20);
        classifierWorkflow.recordReview(16, 20);

        expect(get(classifierWorkflow.workflow)).toMatchObject({
            confirmedPredictions: 34,
            reviewedSamples: 40,
            latestConfirmedPredictions: 16,
            latestReviewedSamples: 20
        });
    });

    it('resets agreement whenever the workflow closes or reopens', () => {
        classifierWorkflow.openRefine('existing', 'classifier-id', 'Zebras', [
            'positive',
            'negative'
        ]);
        classifierWorkflow.recordReview(9, 10);
        classifierWorkflow.close();
        classifierWorkflow.openRefine('existing', 'classifier-id', 'Zebras', [
            'positive',
            'negative'
        ]);

        expect(get(classifierWorkflow.workflow)).toMatchObject({
            confirmedPredictions: 0,
            reviewedSamples: 0,
            latestConfirmedPredictions: null,
            latestReviewedSamples: null
        });
    });
});
