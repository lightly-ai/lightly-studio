import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '$lib/api/ApiError';
import { fetchTickData } from './fetchTickData';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getTickData: vi.fn()
}));

const { getTickData } = await import('$lib/api/lightly_studio_local/sdk.gen');

const params = { datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 3 };

describe('fetchTickData', () => {
    it('rejects with the API error on an HTTP error', async () => {
        const error = new ApiError('Server error', 500);
        vi.mocked(getTickData).mockRejectedValue(error);

        await expect(fetchTickData(params)).rejects.toBe(error);
    });
});
