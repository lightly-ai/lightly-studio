import { describe, expect, it } from 'vitest';
import { getLabelingModelsRefetchInterval } from './getLabelingModelsRefetchInterval';

const POLL_INTERVAL_MS = 5_000;
const model = { id: 'detector', task: 'object_detection' as const, class_names: ['cat'] };

describe('getLabelingModelsRefetchInterval', () => {
    it('polls before the first response', () => {
        expect(getLabelingModelsRefetchInterval(undefined)).toBe(POLL_INTERVAL_MS);
    });

    it('polls while a model is still loading', () => {
        expect(getLabelingModelsRefetchInterval({ models: [], has_loading_models: true })).toBe(
            POLL_INTERVAL_MS
        );
        expect(
            getLabelingModelsRefetchInterval({ models: [model], has_loading_models: true })
        ).toBe(POLL_INTERVAL_MS);
    });

    it('stops polling when no model is loading', () => {
        expect(
            getLabelingModelsRefetchInterval({ models: [model], has_loading_models: false })
        ).toBe(false);
        expect(getLabelingModelsRefetchInterval({ models: [], has_loading_models: false })).toBe(
            false
        );
    });
});
