import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from './useImageFilters';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local/types.gen';
import { SortDirection } from '$lib/api/lightly_studio_local/types.gen';

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
            const sort: SortFieldExpr[] = [
                {
                    source: 'image',
                    field_name: 'score',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ];

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
