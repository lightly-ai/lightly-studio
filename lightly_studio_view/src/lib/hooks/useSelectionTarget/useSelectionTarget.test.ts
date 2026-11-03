import { describe, expect, it, vi } from 'vitest';
import { getSelectionTarget } from './useSelectionTarget';

const sampleFilter = { sample_filter: { tag_ids: ['s'] } };
const annotationFilter = { sample_filter: { tag_ids: ['a'] } };

const state = vi.hoisted(() => ({
    sampleIds: new Set<string>(),
    cropIds: new Set<string>(),
    sampleSnapshot: null as unknown,
    annotationSnapshot: null as unknown
}));

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { readable, writable } = await import('svelte/store');
    return {
        useGlobalStorage: () => ({
            getSelectedSampleIds: () => readable(state.sampleIds),
            selectedSampleAnnotationCropIds: writable({ c1: state.cropIds }),
            getSelectAllSnapshot: () => readable(state.sampleSnapshot),
            getSelectAllAnnotationSnapshot: () => readable(state.annotationSnapshot)
        })
    };
});

describe('getSelectionTarget', () => {
    it('returns the select-all filter when the selection is unchanged', () => {
        state.sampleIds = new Set(['a', 'b', 'c']);
        state.sampleSnapshot = { filter: sampleFilter, size: 3 };

        expect(getSelectionTarget('c1', 'images')).toEqual({
            kind: 'filter',
            filter: sampleFilter,
            size: 3
        });
    });

    it('returns the IDs after the user unticks items from a select-all', () => {
        state.sampleIds = new Set(['a', 'b']);
        state.sampleSnapshot = { filter: sampleFilter, size: 3 };

        expect(getSelectionTarget('c1', 'images')).toEqual({ kind: 'ids', ids: ['a', 'b'] });
    });

    it('returns the IDs when there is no select-all snapshot', () => {
        state.sampleIds = new Set(['a']);
        state.sampleSnapshot = null;

        expect(getSelectionTarget('c1', 'images')).toEqual({ kind: 'ids', ids: ['a'] });
    });

    it('uses annotation crop IDs on the annotations grid', () => {
        state.sampleIds = new Set(['ignored']);
        state.sampleSnapshot = { filter: sampleFilter, size: 1 };
        state.cropIds = new Set(['x', 'y']);
        state.annotationSnapshot = { filter: annotationFilter, size: 2 };

        expect(getSelectionTarget('c1', 'annotations')).toEqual({
            kind: 'filter',
            filter: annotationFilter,
            size: 2
        });

        state.annotationSnapshot = null;
        expect(getSelectionTarget('c1', 'annotations')).toEqual({ kind: 'ids', ids: ['x', 'y'] });
    });
});
