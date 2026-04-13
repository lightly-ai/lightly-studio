import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
import { fetchCollection } from './fetchCollection';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    readCollection: vi.fn()
}));

const { readCollection } = await import('$lib/api/lightly_studio_local/sdk.gen');

describe('fetchCollection', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should fetch collection successfully', async () => {
        const mockCollection: CollectionViewWithCount = {
            collection_id: 'test-id',
            name: 'Test Collection',
            parent_collection_id: null,
            sample_type: 'IMAGE',
            num_samples: 10
        } as unknown as CollectionViewWithCount;

        vi.mocked(readCollection).mockResolvedValue({
            data: mockCollection,
            error: undefined,
            request: {} as Request,
            response: {} as Response
        });

        const result = await fetchCollection('test-id');

        expect(result).toEqual(mockCollection);
        expect(readCollection).toHaveBeenCalledWith({
            path: { collection_id: 'test-id' }
        });
    });

    it('should throw error when API call fails', async () => {
        vi.mocked(readCollection).mockRejectedValue(new Error('API Error'));

        await expect(fetchCollection('test-id')).rejects.toThrow('Collection test-id not found');
    });
});
