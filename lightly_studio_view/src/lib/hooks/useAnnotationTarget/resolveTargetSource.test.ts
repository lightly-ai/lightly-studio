import { describe, expect, it } from 'vitest';
import {
    DEFAULT_SOURCE_NAME,
    getTargetBlockedReason,
    PICK_SOURCE_MESSAGE,
    pickInitialSource,
    resolveTargetSource
} from './resolveTargetSource';

describe('resolveTargetSource', () => {
    it('uses the chosen source, also one that does not exist yet', () => {
        expect(resolveTargetSource('new_source', ['ground_truth', 'predictions'])).toBe(
            'new_source'
        );
    });

    it('uses the only source', () => {
        expect(resolveTargetSource(null, ['ground_truth'])).toBe('ground_truth');
    });

    it('uses the backend default when there is no source', () => {
        expect(resolveTargetSource(undefined, [])).toBe(DEFAULT_SOURCE_NAME);
    });

    it('picks nothing when there are several sources', () => {
        expect(resolveTargetSource(null, ['ground_truth', 'predictions'])).toBeNull();
    });
});

describe('getTargetBlockedReason', () => {
    it('blocks while no source is picked', () => {
        expect(getTargetBlockedReason(null, false)).toBe(PICK_SOURCE_MESSAGE);
    });

    it('blocks a hidden target', () => {
        expect(getTargetBlockedReason('model_v1', true)).toBe(
            'model_v1 is hidden. Show it in the Annotations panel to add annotations to it.'
        );
    });

    it('allows a shown target', () => {
        expect(getTargetBlockedReason('model_v1', false)).toBeNull();
    });
});

describe('pickInitialSource', () => {
    const two = ['labels', 'predictions'];

    it('leaves a chosen source alone', () => {
        expect(
            pickInitialSource({
                chosenSource: 'labels',
                sourceNames: two,
                defaultSource: 'predictions'
            })
        ).toBeNull();
    });

    it('seeds the only source', () => {
        expect(
            pickInitialSource({ chosenSource: null, sourceNames: ['a'], defaultSource: undefined })
        ).toBe('a');
    });

    it('seeds the default', () => {
        expect(
            pickInitialSource({
                chosenSource: null,
                sourceNames: two,
                defaultSource: 'predictions'
            })
        ).toBe('predictions');
    });

    it('ignores a default that was deleted', () => {
        expect(
            pickInitialSource({ chosenSource: null, sourceNames: two, defaultSource: 'gone' })
        ).toBeNull();
    });

    it('picks nothing with two sources and no default', () => {
        expect(
            pickInitialSource({ chosenSource: null, sourceNames: two, defaultSource: undefined })
        ).toBeNull();
    });
});
