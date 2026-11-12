import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { prefetchMcapTick } from './prefetchMcapTick';
import { createMcapTickPrefetchExecutor } from './createMcapTickPrefetchExecutor';
import { prefetchInChunks } from './prefetchInChunks';

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
    afterEach(() => vi.useRealTimers());

    it.each(['tick-data', 'tick-details'])(
        'aborts a hung %s request after 30 seconds and allows a fresh retry',
        async (queryKey) => {
            vi.useFakeTimers();
            let requestSignal: AbortSignal | undefined;
            const loadData = vi.fn(({ signal }: { signal: AbortSignal }) => {
                requestSignal = signal;
                return new Promise(() => {});
            });
            const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
            client.setQueryDefaults(['tick-details'], { queryFn: async () => ({}) });
            client.setQueryDefaults(['tick-data'], { queryFn: async () => ({}) });
            client.setQueryDefaults([queryKey], { queryFn: loadData });
            try {
                const pending = prefetchMcapTick(client, params);
                const timedOut = expect(pending).rejects.toThrow(
                    'Loading frame timed out. Please try again.'
                );
                await vi.advanceTimersByTimeAsync(30_000);
                await timedOut;
                expect(requestSignal?.aborted).toBe(true);

                const retryData = vi.fn().mockResolvedValue({});
                client.setQueryDefaults([queryKey], { queryFn: retryData });
                await prefetchMcapTick(client, params);

                expect(retryData).toHaveBeenCalledOnce();
                expect(client.getQueryData([queryKey])).toEqual({});
            } finally {
                client.clear();
            }
        }
    );

    it('records a timed-out tick as failed and continues buffering the next chunk', async () => {
        vi.useFakeTimers();
        const client = {
            ensureQueryData: vi
                .fn()
                .mockResolvedValueOnce({})
                .mockImplementationOnce(() => new Promise(() => {}))
                .mockResolvedValue({}),
            cancelQueries: vi.fn().mockResolvedValue(undefined)
        } as unknown as QueryClient;
        const onStateChange = vi.fn();
        const executor = createMcapTickPrefetchExecutor({
            client,
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'sequence-1',
            getDisplayFrameId: () => 'base_link',
            getTicks: () => [0, 1].map((seq_number) => ({ seq_number, timestamp_ns: null })),
            onStateChange
        });
        const pending = prefetchInChunks({
            requestId: 'timeout-test',
            indexes: [0, 1],
            chunkSize: 1,
            delayMs: 200,
            prefetchRange: executor.prefetchRanges,
            isCurrent: () => true
        });

        await vi.advanceTimersByTimeAsync(30_200);
        await pending;

        expect(onStateChange).toHaveBeenLastCalledWith(
            new Set([1]),
            new Map([
                [
                    0,
                    expect.objectContaining({
                        message: 'Loading frame timed out. Please try again.'
                    })
                ]
            ])
        );
    });

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
