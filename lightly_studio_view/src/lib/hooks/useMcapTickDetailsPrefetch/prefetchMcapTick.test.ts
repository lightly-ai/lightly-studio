import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { prefetchMcapTick } from './prefetchMcapTick';

vi.mock('$lib/hooks/useTickData/getTickDataOptions', () => ({
    getTickDataOptions: vi.fn(() => ({ queryKey: ['tick-data'] }))
}));
vi.mock('$lib/hooks/useTickDetails/getTickDetailsOptions', () => ({
    getTickDetailsOptions: vi.fn(() => ({ queryKey: ['tick-details'] }))
}));

const params = {
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 4,
    displayFrameId: 'base_link'
};

describe('prefetchMcapTick', () => {
    beforeEach(() => vi.clearAllMocks());

    it('caches the tick details and the tick data with one request each', async () => {
        const client = { ensureQueryData: vi.fn().mockResolvedValue({}) } as unknown as QueryClient;

        await prefetchMcapTick(client, params);

        expect(getTickDetailsOptions).toHaveBeenCalledWith(params);
        expect(getTickDataOptions).toHaveBeenCalledWith(params);
        expect(client.ensureQueryData).toHaveBeenCalledTimes(2);
        expect(client.ensureQueryData).toHaveBeenCalledWith({ queryKey: ['tick-details'] });
        expect(client.ensureQueryData).toHaveBeenCalledWith({ queryKey: ['tick-data'] });
    });

    it('propagates errors so a failed tick cannot be marked buffered', async () => {
        const error = new Error('Tick data unavailable');
        const client = {
            ensureQueryData: vi.fn().mockResolvedValueOnce({}).mockRejectedValueOnce(error)
        } as unknown as QueryClient;

        await expect(prefetchMcapTick(client, params)).rejects.toBe(error);
    });
});
