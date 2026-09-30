import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import { useSimilaritySort } from './useSimilaritySort';

const search = { queryText: 'cats', embedding: [0.1, 0.2] };

describe('useSimilaritySort', () => {
    beforeEach(() => {
        const { resetOnNewSearch } = useSimilaritySort();
        resetOnNewSearch(undefined);
        resetOnNewSearch(search);
    });

    it('sorts descending by default and toggles the direction', () => {
        const { direction, similaritySortBy, toggleDirection } = useSimilaritySort();
        expect(get(direction)).toBe(SortDirection.DESC);

        toggleDirection();

        expect(get(direction)).toBe(SortDirection.ASC);
        expect(get(similaritySortBy)).toEqual({
            source: 'similarity',
            direction: SortDirection.ASC
        });
    });

    it('keeps the direction while the search stays the same', () => {
        const { direction, toggleDirection, resetOnNewSearch } = useSimilaritySort();
        toggleDirection();

        resetOnNewSearch(search);

        expect(get(direction)).toBe(SortDirection.ASC);
    });

    it('resets to descending on a new search', () => {
        const { direction, toggleDirection, resetOnNewSearch } = useSimilaritySort();
        toggleDirection();

        resetOnNewSearch({ ...search });

        expect(get(direction)).toBe(SortDirection.DESC);
    });
});
