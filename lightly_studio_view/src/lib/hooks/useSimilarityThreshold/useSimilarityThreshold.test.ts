import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useSimilarityThreshold } from './useSimilarityThreshold';

const search = { queryText: 'cats', embedding: [0.1, 0.2] };
const scope = { search, collectionId: 'col-1', gridType: 'images' };

describe('useSimilarityThreshold', () => {
    beforeEach(() => {
        const { resetOnScopeChange } = useSimilarityThreshold();
        resetOnScopeChange(scope);
    });

    it('is off by default and can be set and cleared', () => {
        const { threshold, setThreshold, clearThreshold } = useSimilarityThreshold();
        expect(get(threshold)).toBeNull();

        setThreshold(-0.42);
        expect(get(threshold)).toBe(-0.42);

        clearThreshold();
        expect(get(threshold)).toBeNull();
    });

    it('keeps the threshold while the scope stays the same', () => {
        const { threshold, setThreshold, resetOnScopeChange } = useSimilarityThreshold();
        setThreshold(0.5);

        resetOnScopeChange({ ...scope });

        expect(get(threshold)).toBe(0.5);
    });

    it.each([
        ['a new search', { search: { ...search } }],
        ['a cleared search', { search: undefined }],
        ['a collection change', { collectionId: 'col-2' }],
        ['a tab change', { gridType: 'annotations' }]
    ])('clears the threshold on %s', (_name, change) => {
        const { threshold, setThreshold, resetOnScopeChange } = useSimilarityThreshold();
        setThreshold(0.5);

        resetOnScopeChange({ ...scope, ...change });

        expect(get(threshold)).toBeNull();
    });
});
