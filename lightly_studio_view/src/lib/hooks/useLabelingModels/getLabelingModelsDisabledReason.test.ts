import { describe, expect, it } from 'vitest';
import { getLabelingModelsDisabledReason } from './getLabelingModelsDisabledReason';

const MODEL = { id: 'ltdetrv2-s-coco', task: 'object_detection' as const, class_names: ['cat'] };

describe('getLabelingModelsDisabledReason', () => {
    it('returns null when models are available', () => {
        expect(
            getLabelingModelsDisabledReason({
                models: { models: [MODEL], unavailable_reason: null },
                isError: false
            })
        ).toBeNull();
    });

    it('returns the reason of the backend', () => {
        expect(
            getLabelingModelsDisabledReason({
                models: { models: [], unavailable_reason: 'Set the URL.' },
                isError: false
            })
        ).toBe('Set the URL.');
    });

    it('returns a reason when the server has no models', () => {
        expect(
            getLabelingModelsDisabledReason({
                models: { models: [], unavailable_reason: null },
                isError: false
            })
        ).toBe('No labeling model is registered.');
    });

    it('returns a reason while loading and after an error', () => {
        expect(getLabelingModelsDisabledReason({ models: undefined, isError: false })).toBe(
            'Loading the labeling models…'
        );
        expect(getLabelingModelsDisabledReason({ models: undefined, isError: true })).toBe(
            'Could not load the labeling models.'
        );
    });
});
