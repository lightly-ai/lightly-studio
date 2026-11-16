import { describe, expect, it } from 'vitest';
import { LOADING_SOURCES_MESSAGE, PICK_SOURCE_MESSAGE, SOURCES_ERROR_MESSAGE } from './messages';
import { DEFAULT_SOURCE_NAME, isPickRemoved, resolveTargetSource } from './resolveTargetSource';

const two = ['labels', 'predictions'];
const base = {
    pick: undefined,
    typedSource: null,
    sourceNames: two,
    isError: false,
    hiddenSources: []
};

describe('resolveTargetSource', () => {
    it('uses a picked source that exists', () => {
        expect(resolveTargetSource({ ...base, pick: 'predictions' })).toEqual({
            targetSource: 'predictions',
            blockedReason: null
        });
    });

    it('drops a remembered pick whose source is gone, instead of re-creating it', () => {
        expect(resolveTargetSource({ ...base, pick: 'deleted' })).toEqual({
            targetSource: null,
            blockedReason: PICK_SOURCE_MESSAGE
        });
    });

    it('uses a pick typed on this page before its source exists', () => {
        expect(
            resolveTargetSource({ ...base, pick: 'review', typedSource: 'review' }).targetSource
        ).toBe('review');
    });

    it('uses the only source, and the backend default without sources', () => {
        expect(resolveTargetSource({ ...base, sourceNames: ['a'] }).targetSource).toBe('a');
        expect(resolveTargetSource({ ...base, sourceNames: [] }).targetSource).toBe(
            DEFAULT_SOURCE_NAME
        );
    });

    it('picks nothing among several sources and asks for a pick', () => {
        expect(resolveTargetSource(base)).toEqual({
            targetSource: null,
            blockedReason: PICK_SOURCE_MESSAGE
        });
    });

    it('blocks a hidden target', () => {
        expect(resolveTargetSource({ ...base, pick: 'labels', hiddenSources: ['labels'] })).toEqual(
            {
                targetSource: 'labels',
                blockedReason:
                    'labels is hidden. Show it in the Annotations panel to add annotations to it.'
            }
        );
    });

    it('knows no target until the sources load, also with a pick', () => {
        expect(resolveTargetSource({ ...base, pick: 'labels', sourceNames: undefined })).toEqual({
            targetSource: null,
            blockedReason: LOADING_SOURCES_MESSAGE
        });
        expect(
            resolveTargetSource({ ...base, sourceNames: undefined, isError: true }).blockedReason
        ).toBe(SOURCES_ERROR_MESSAGE);
    });
});

describe('isPickRemoved', () => {
    const previousNames = ['labels', 'predictions'];

    it('is true when the picked source left the list', () => {
        expect(isPickRemoved({ pick: 'labels', previousNames, nextNames: ['predictions'] })).toBe(
            true
        );
    });

    it('is true when one name left and one came, like a rename', () => {
        expect(
            isPickRemoved({
                pick: 'labels',
                previousNames,
                nextNames: ['labels_v2', 'predictions']
            })
        ).toBe(true);
    });

    it('is false for a picked source that is still listed', () => {
        expect(
            isPickRemoved({ pick: 'predictions', previousNames, nextNames: ['predictions'] })
        ).toBe(false);
    });

    it('is false for a typed new source that was never listed', () => {
        expect(isPickRemoved({ pick: 'review', previousNames, nextNames: ['predictions'] })).toBe(
            false
        );
    });
});
