import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as loadDimensionBoundsModule from '$lib/services/loadDimensionBounds';
import { waitFor } from '@testing-library/svelte';
import { get, writable } from 'svelte/store';

// We need to dynamically import useDimensions after mocking, and reset modules
// between tests so the module-level state (lastCollectionId) is fresh.

describe('useDimensions', () => {
    let loadDimensionBoundsMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        vi.restoreAllMocks();

        loadDimensionBoundsMock = vi
            .spyOn(loadDimensionBoundsModule, 'loadDimensionBounds')
            .mockResolvedValue({
                data: {
                    min_width: 10,
                    max_width: 100,
                    min_height: 20,
                    max_height: 200
                }
            });
    });

    it('calls loadInitialDimensionBounds when collection_id is provided', async () => {
        const { useDimensions } = await import('./useDimensions');
        useDimensions('test-collection');

        expect(loadDimensionBoundsMock).toHaveBeenCalledWith({
            collection_id: 'test-collection'
        });
    });

    it('does not call loadInitialDimensionBounds when collection_id is not provided', async () => {
        const { useDimensions } = await import('./useDimensions');
        useDimensions();

        expect(loadDimensionBoundsMock).not.toHaveBeenCalled();
    });

    it('updates dimensionsValues when updateDimensionsValues is called', async () => {
        const { useDimensions } = await import('./useDimensions');
        const { dimensionsValues, updateDimensionsValues } = useDimensions();
        const newValues = { min_width: 5, max_width: 50, min_height: 10, max_height: 100 };

        updateDimensionsValues(newValues);

        expect(get(dimensionsValues)).toEqual(newValues);
    });

    it('updates dimensionsBounds when updateDimensionsBounds is called', async () => {
        const { useDimensions } = await import('./useDimensions');
        const { dimensionsBounds, updateDimensionsBounds } = useDimensions();
        const newValues = { min_width: 5, max_width: 50, min_height: 10, max_height: 100 };

        updateDimensionsBounds(newValues);

        expect(get(dimensionsBounds)).toEqual(newValues);
    });

    it('does not refetch when called with the same collection_id', async () => {
        const { useDimensions } = await import('./useDimensions');

        useDimensions('collection-a');
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(1);

        // Second call with same id should not trigger another fetch
        useDimensions('collection-a');
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(1);
    });

    it('resets stores and refetches when called with a different collection_id', async () => {
        const { useDimensions } = await import('./useDimensions');

        // Use unique IDs that no other test has used
        useDimensions('collection-x');
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(1);

        // Wait for the first fetch to resolve and populate the stores
        await waitFor(() => {
            const { dimensionsBounds } = useDimensions();
            expect(get(dimensionsBounds)).not.toBeNull();
        });

        // Now switch to a different collection
        useDimensions('collection-y');
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(2);
        expect(loadDimensionBoundsMock).toHaveBeenLastCalledWith({
            collection_id: 'collection-y'
        });

        // Verify stores get repopulated after the fetch resolves
        const { dimensionsBounds, dimensionsValues } = useDimensions();
        await waitFor(() => {
            expect(get(dimensionsBounds)).toEqual({
                min_width: 10,
                max_width: 100,
                min_height: 20,
                max_height: 200
            });
            expect(get(dimensionsValues)).toEqual({
                min_width: 10,
                max_width: 100,
                min_height: 20,
                max_height: 200
            });
        });
    });

    it('loads and refetches when collection_id readable store changes', async () => {
        const { useDimensions } = await import('./useDimensions');
        const collectionId = writable('collection-store-a');
        const { dimensionsValues } = useDimensions(collectionId);

        get(dimensionsValues);
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(1);
        expect(loadDimensionBoundsMock).toHaveBeenLastCalledWith({
            collection_id: 'collection-store-a'
        });

        collectionId.set('collection-store-a');
        get(dimensionsValues);
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(1);

        collectionId.set('collection-store-b');
        get(dimensionsValues);
        expect(loadDimensionBoundsMock).toHaveBeenCalledTimes(2);
        expect(loadDimensionBoundsMock).toHaveBeenLastCalledWith({
            collection_id: 'collection-store-b'
        });
    });
});
