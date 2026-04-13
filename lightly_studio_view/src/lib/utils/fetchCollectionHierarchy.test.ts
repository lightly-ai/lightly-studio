import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { fetchCollectionHierarchy } from './fetchCollectionHierarchy';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    readCollectionHierarchy: vi.fn()
}));

const { readCollectionHierarchy } = await import('$lib/api/lightly_studio_local/sdk.gen');

describe('fetchCollectionHierarchy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should fetch hierarchy successfully', async () => {
        const mockHierarchy: CollectionView[] = [
            {
                collection_id: 'dataset-id',
                name: 'Dataset',
                parent_collection_id: null,
                sample_type: 'IMAGE'
            } as unknown as CollectionView,
            {
                collection_id: 'collection-id',
                name: 'Collection',
                parent_collection_id: 'dataset-id',
                sample_type: 'IMAGE'
            } as unknown as CollectionView
        ];

        vi.mocked(readCollectionHierarchy).mockResolvedValue({
            data: mockHierarchy,
            error: undefined,
            request: {} as Request,
            response: {} as Response
        });

        const result = await fetchCollectionHierarchy('dataset-id');

        expect(result).toEqual(mockHierarchy);
        expect(readCollectionHierarchy).toHaveBeenCalledWith({
            path: { collection_id: 'dataset-id' }
        });
    });

    it('should throw error when API call fails with status', async () => {
        const apiError = { status: 404, message: 'Not found' };
        vi.mocked(readCollectionHierarchy).mockRejectedValue(apiError);

        await expect(fetchCollectionHierarchy('dataset-id')).rejects.toEqual(apiError);
    });

    it('should throw formatted error when API call fails without status', async () => {
        vi.mocked(readCollectionHierarchy).mockRejectedValue(new Error('Network error'));

        await expect(fetchCollectionHierarchy('dataset-id')).rejects.toThrow(
            'Error loading collection hierarchy: Network error'
        );
    });

    it('should throw formatted error when non-Error object is thrown', async () => {
        vi.mocked(readCollectionHierarchy).mockRejectedValue('Some error');

        await expect(fetchCollectionHierarchy('dataset-id')).rejects.toThrow(
            'Error loading collection hierarchy: Some error'
        );
    });
});
