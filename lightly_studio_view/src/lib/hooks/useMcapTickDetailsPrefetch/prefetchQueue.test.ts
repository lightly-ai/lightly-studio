import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/svelte-query';
import { createPrefetchQueue } from './prefetchQueue';
import { createPrefetchSession } from './prefetchSession';
import { prefetchMcapTick } from './prefetchMcapTick';

vi.mock('./prefetchMcapTick', () => ({ prefetchMcapTick: vi.fn() }));

const ticks = Array.from({ length: 6 }, (_, seq_number) => ({ seq_number, timestamp_ns: null }));
const prefetchMock = vi.mocked(prefetchMcapTick);

function createQueue() {
    return createPrefetchQueue({
        client: {} as QueryClient,
        getDatasetId: () => 'dataset-1',
        getSequenceId: () => 'sequence-1',
        getDisplayFrameId: () => 'base_link',
        getTicks: () => ticks,
        isCurrentSession: () => true,
        onStateChange: vi.fn()
    });
}

describe('prefetchQueue', () => {
    beforeEach(() => vi.clearAllMocks());

    it('prefetches every enqueued tick and records completed indexes', async () => {
        prefetchMock.mockResolvedValue(undefined);
        const session = createPrefetchSession('request-1');

        await createQueue().enqueue(session, [1, 3]);

        expect(prefetchMock.mock.calls.map(([, params]) => params.seqNumber)).toEqual([1, 3]);
        expect(session.completed).toEqual(new Set([1, 3]));
    });

    it('limits the number of active requests', async () => {
        const resolvers: Array<() => void> = [];
        prefetchMock.mockImplementation(
            () => new Promise<void>((resolve) => resolvers.push(resolve))
        );
        const session = createPrefetchSession('request-1');
        const promise = createQueue().enqueue(session, [0, 1, 2, 3, 4, 5]);

        await vi.waitFor(() => expect(prefetchMock).toHaveBeenCalledTimes(4));
        expect(resolvers).toHaveLength(4);

        for (const expectedCalls of [5, 6]) {
            resolvers.shift()?.();
            await vi.waitFor(() => expect(prefetchMock).toHaveBeenCalledTimes(expectedCalls));
        }
        while (resolvers.length > 0) resolvers.shift()?.();
        await promise;
    });

    it('records failed ticks without rejecting the queue promise', async () => {
        const error = new Error('prefetch failed');
        prefetchMock.mockRejectedValueOnce(error);
        const session = createPrefetchSession('request-1');

        await createQueue().enqueue(session, [2]);

        expect(session.completed).toEqual(new Set());
        expect(session.errors.get(2)).toBe(error);
    });
});
