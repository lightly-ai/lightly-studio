import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useDimensions } from './useDimensions';
import * as loadDimensionBoundsModule from '$lib/services/loadDimensionBounds';
import * as useSessionStorageModule from '$lib/hooks/useSessionStorage/useSessionStorage';
import { waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';

describe('useDimensions', () => {
    const mockSet = vi.fn();
    const mockSessionStorage = {
        set: mockSet,
        subscribe: vi.fn(),
        update: vi.fn()
    };

    const setup = () => {
        // Mock useSessionStorage
        vi.spyOn(useSessionStorageModule, 'useSessionStorage').mockReturnValue(mockSessionStorage);

        // Mock loadDimensionBounds
        const loadDimensionBoundsMock = vi
            .spyOn(loadDimensionBoundsModule, 'loadDimensionBounds')
            .mockResolvedValue({
                data: {
                    min_width: 10,
                    max_width: 100,
                    min_height: 20,
                    max_height: 200
                }
            });

        // Spy on console.error
        vi.spyOn(console, 'error').mockImplementation(() => {});

        return {
            loadDimensionBoundsMock
        };
    };

    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('calls loadInitialDimensionBounds when dataset_id is provided', async () => {
        const { loadDimensionBoundsMock } = setup();
        useDimensions('test-dataset');

        expect(loadDimensionBoundsMock).toHaveBeenCalledWith({
            dataset_id: 'test-dataset'
        });
    });

    it('does not call loadInitialDimensionBounds when dataset_id is not provided', async () => {
        const { loadDimensionBoundsMock } = setup();
        useDimensions();

        expect(loadDimensionBoundsMock).not.toHaveBeenCalled();
    });

    it('updates dimensionsValues when updateDimensionsValues is called', async () => {
        setup();
        const { dimensionsValues, updateDimensionsValues } = useDimensions();
        const newValues = { min_width: 5, max_width: 50, min_height: 10, max_height: 100 };

        updateDimensionsValues(newValues);

        await waitFor(() => {
            expect(get(dimensionsValues)).toEqual(newValues);
        });
    });

    it('updates dimensionsBounds when updateDimensionsBounds is called', async () => {
        setup();
        const { dimensionsBounds, updateDimensionsBounds } = useDimensions();
        const newValues = { min_width: 5, max_width: 50, min_height: 10, max_height: 100 };

        updateDimensionsBounds(newValues);

        await waitFor(() => {
            expect(get(dimensionsBounds)).toEqual(newValues);
        });
    });
});
