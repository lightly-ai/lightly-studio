import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useConfusionMatrixSettings, useExpandedEvaluationRun } from './useEvaluationPanelState';

describe('useEvaluationPanelState', () => {
    it('keeps the expanded run per collection for the next panel', () => {
        useExpandedEvaluationRun('images-a').set('run-1');

        // A reopened panel calls the hook again.
        expect(get(useExpandedEvaluationRun('images-a'))).toBe('run-1');
        expect(get(useExpandedEvaluationRun('images-b'))).toBeNull();
    });

    it('keeps the confusion matrix settings per run', () => {
        const settings = {
            config: {
                mode: 'topN' as const,
                n: 8,
                sortBy: 'most-confused' as const,
                manualClasses: []
            },
            color: { intensity: 2, logScale: false }
        };
        useConfusionMatrixSettings('run-1').set(settings);

        expect(get(useConfusionMatrixSettings('run-1'))).toEqual(settings);
        expect(get(useConfusionMatrixSettings('run-2'))).toBeNull();
    });
});
