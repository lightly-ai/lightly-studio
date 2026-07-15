import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { useExportSamplesCount } from './useExportSamplesCount';

const mocks = vi.hoisted(() => ({
    exportCollectionStats: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionStats: mocks.exportCollectionStats
}));

const defaultProps: Parameters<typeof useExportSamplesCount>[0] = {
    collection_id: 'test-collection',
    includeFilter: {
        tag_ids: ['tag1', 'tag2']
    }
} as const;

describe('useExportStats', () => {
    beforeEach(vi.resetAllMocks);

    it('should call export stats endpoint', () => {
        mocks.exportCollectionStats.mockResolvedValueOnce({ data: 0 });
        useExportSamplesCount(defaultProps);
        expect(mocks.exportCollectionStats).toHaveBeenCalledWith({
            path: { collection_id: 'test-collection' },
            body: {
                include: defaultProps.includeFilter,
                exclude: undefined,
                collection_filter: undefined
            }
        });
    });

    it('should reflect loading state', async () => {
        const expectedCount = 42;
        mocks.exportCollectionStats.mockResolvedValueOnce({ data: expectedCount });
        const { isLoading, count, error } = useExportSamplesCount(defaultProps);

        // Initial state
        expect(get(isLoading)).toBe(true);
        expect(get(count)).toBe(0);
        expect(get(error)).toBeUndefined();

        await vi.waitFor(() => {
            expect(get(isLoading)).toBe(false);
            expect(get(count)).toBe(expectedCount);
            expect(get(error)).toBeUndefined();
        });
    });

    it('should handle errors', async () => {
        const errorMessage = 'API Error';
        mocks.exportCollectionStats.mockRejectedValueOnce(new Error(errorMessage));

        const { isLoading, count, error } = useExportSamplesCount(defaultProps);

        // Wait for error state
        await vi.waitFor(() => {
            expect(get(isLoading)).toBe(false);
            expect(get(count)).toBe(0);
            expect(get(error)).toBe(errorMessage);
        });
    });

    it('should return count when collectionFilter is provided with includeFilter', async () => {
        mocks.exportCollectionStats.mockResolvedValueOnce({ data: 10 });
        const collectionFilter = {
            filter_type: 'image' as const,
            sample_filter: { tag_ids: ['t1'] }
        };
        const { count } = useExportSamplesCount({
            collection_id: 'test-collection',
            includeFilter: { tag_ids: ['tag1'] },
            collectionFilter
        });
        await vi.waitFor(() => {
            expect(get(count)).toBe(10);
        });
    });

    it('should return count when only collectionFilter is set', async () => {
        mocks.exportCollectionStats.mockResolvedValueOnce({ data: 5 });
        const collectionFilter = { filter_type: 'image' as const };
        const { count } = useExportSamplesCount({
            collection_id: 'test-collection',
            collectionFilter
        });
        await vi.waitFor(() => {
            expect(get(count)).toBe(5);
        });
    });
});
