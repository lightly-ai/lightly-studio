import { describe, expect, it } from 'vitest';
import { getLabelingModelsRefetchInterval } from './getLabelingModelsRefetchInterval';

describe('getLabelingModelsRefetchInterval', () => {
    it('polls until a model is ready', () => {
        expect(getLabelingModelsRefetchInterval(undefined)).toBe(5_000);
        expect(getLabelingModelsRefetchInterval({ models: [] })).toBe(5_000);
    });

    it('stops polling when a model is ready', () => {
        const model = { id: 'detector', task: 'object_detection' as const, class_names: ['cat'] };
        expect(getLabelingModelsRefetchInterval({ models: [model] })).toBe(false);
    });
});
