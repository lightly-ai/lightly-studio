import { describe, expect, it } from 'vitest';
import {
    CUBOID_SOURCE_MESSAGES,
    isCuboidPickRemoved,
    resolveCuboidTargetSource
} from './resolveCuboidTargetSource';

const base = {
    pick: undefined,
    typedSource: null,
    sourceNames: ['labels', 'predictions'],
    isError: false
};

describe('resolveCuboidTargetSource', () => {
    it('uses a picked source that exists', () => {
        expect(resolveCuboidTargetSource({ ...base, pick: 'predictions' })).toEqual({
            targetSource: 'predictions',
            blockedReason: null,
            needsPick: false
        });
    });

    it('asks for a pick when the remembered source is gone', () => {
        expect(resolveCuboidTargetSource({ ...base, pick: 'deleted' })).toEqual({
            targetSource: null,
            blockedReason: null,
            needsPick: true
        });
    });

    it('uses a name typed on this page before its source exists', () => {
        expect(
            resolveCuboidTargetSource({ ...base, pick: 'review', typedSource: 'review' })
        ).toEqual({ targetSource: 'review', blockedReason: null, needsPick: false });
    });

    it('uses the only source without a pick', () => {
        expect(resolveCuboidTargetSource({ ...base, sourceNames: ['labels'] })).toEqual({
            targetSource: 'labels',
            blockedReason: null,
            needsPick: false
        });
    });

    it('asks for a pick when there are no sources', () => {
        expect(resolveCuboidTargetSource({ ...base, sourceNames: [] })).toEqual({
            targetSource: null,
            blockedReason: null,
            needsPick: true
        });
    });

    it('asks for a pick among several sources', () => {
        expect(resolveCuboidTargetSource(base)).toEqual({
            targetSource: null,
            blockedReason: null,
            needsPick: true
        });
    });

    it('blocks while the sources load, also with a pick', () => {
        expect(
            resolveCuboidTargetSource({ ...base, pick: 'labels', sourceNames: undefined })
        ).toEqual({
            targetSource: null,
            blockedReason: 'Loading annotation sources…',
            needsPick: false
        });
    });

    it('blocks after a failed load, also with names cached', () => {
        const expected = {
            targetSource: null,
            blockedReason: CUBOID_SOURCE_MESSAGES.error,
            needsPick: false
        };
        expect(resolveCuboidTargetSource({ ...base, pick: 'labels', isError: true })).toEqual(
            expected
        );
        expect(
            resolveCuboidTargetSource({ ...base, sourceNames: undefined, isError: true })
        ).toEqual(expected);
        expect(CUBOID_SOURCE_MESSAGES).toEqual({
            pick: 'Pick where new annotations go.',
            loading: 'Loading annotation sources…',
            error: 'Could not load the annotation sources. Reload the page to add annotations.'
        });
    });
});

describe('isCuboidPickRemoved', () => {
    const previousNames = ['labels', 'predictions'];

    it('is true when the picked source left the list', () => {
        expect(
            isCuboidPickRemoved({ pick: 'labels', previousNames, nextNames: ['predictions'] })
        ).toBe(true);
    });

    it('is true for a rename: one name left and one came', () => {
        expect(
            isCuboidPickRemoved({
                pick: 'labels',
                previousNames,
                nextNames: ['labels_v2', 'predictions']
            })
        ).toBe(true);
    });

    it('is false for a picked source that is still listed', () => {
        expect(
            isCuboidPickRemoved({ pick: 'predictions', previousNames, nextNames: ['predictions'] })
        ).toBe(false);
    });

    it('is false for a typed name that was never listed', () => {
        expect(
            isCuboidPickRemoved({ pick: 'review', previousNames, nextNames: ['predictions'] })
        ).toBe(false);
    });
});
