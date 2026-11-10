import { describe, expect, it } from 'vitest';
import { canStartTraining, isActiveRun, progressPercent } from './TrainModelDialog.helpers';

describe('isActiveRun', () => {
    it('is true while the run trains, predicts, adds predictions or evaluates', () => {
        expect(isActiveRun({ status: 'training' })).toBe(true);
        expect(isActiveRun({ status: 'evaluating' })).toBe(true);
    });

    it('is false for a finished run or no run', () => {
        expect(isActiveRun({ status: 'completed' })).toBe(false);
        expect(isActiveRun({ status: 'failed' })).toBe(false);
        expect(isActiveRun(undefined)).toBe(false);
    });
});

describe('progressPercent', () => {
    it('returns the rounded step share', () => {
        expect(progressPercent({ current_step: 1, total_steps: 3 })).toBe(33);
    });

    it('returns null before the first logged step', () => {
        expect(progressPercent({ current_step: null, total_steps: null })).toBeNull();
    });
});

describe('canStartTraining', () => {
    const valid = {
        trainTagId: 'train',
        valTagId: 'val',
        gtSourceId: 'gt',
        steps: 100,
        isStarting: false
    };

    it('is true for complete inputs', () => {
        expect(canStartTraining(valid)).toBe(true);
    });

    it('is false for the same train and val tag', () => {
        expect(canStartTraining({ ...valid, valTagId: 'train' })).toBe(false);
    });

    it('is false without a ground truth source', () => {
        expect(canStartTraining({ ...valid, gtSourceId: undefined })).toBe(false);
    });

    it('is false for a step count below 1', () => {
        expect(canStartTraining({ ...valid, steps: 0 })).toBe(false);
    });

    it('is false while a start request is pending', () => {
        expect(canStartTraining({ ...valid, isStarting: true })).toBe(false);
    });
});
