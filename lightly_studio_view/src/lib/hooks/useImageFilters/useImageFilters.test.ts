import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from './useImageFilters';

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useImageFilters', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({} as Parameters<typeof updateFilterParams>[0]);
    });

    describe('updateSortBy', () => {
        it('sets imageSortBy to the provided sort fields', () => {
            const { imageSortBy, updateSortBy } = useImageFilters();
            const sort = [{ field: 'score', direction: 'desc' } as never];

            updateSortBy(sort);

            expect(get(imageSortBy)).toEqual(sort);
        });

        it('sets imageSortBy to null when called with null', () => {
            const { imageSortBy, updateSortBy } = useImageFilters();

            updateSortBy(null);

            expect(get(imageSortBy)).toBeNull();
        });
    });
});
