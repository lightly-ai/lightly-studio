import { describe, expect, it, vi } from 'vitest';
import { fetchTickData } from './fetchTickData';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getTickData: vi.fn()
}));

const { getTickData } = await import('$lib/api/lightly_studio_local/sdk.gen');

const params = { datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 3 };

describe('fetchTickData', () => {
    it('throws with the tick number and status on an HTTP error', async () => {
        vi.mocked(getTickData).mockResolvedValue({
            data: undefined,
            error: { detail: 'Server error' },
            request: new Request('http://localhost'),
            response: new Response(null, { status: 500 })
        } as Awaited<ReturnType<typeof getTickData>>);

        await expect(fetchTickData(params)).rejects.toThrow('Could not load tick 3 (500).');
    });
});
