import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { prefetchInChunks } from './prefetchInChunks';

describe('prefetchInChunks', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('loads only requested indexes when one chunk contains separate ranges', async () => {
        const prefetchRange = vi.fn().mockResolvedValue(undefined);
        await prefetchInChunks({
            requestId: 'request-1',
            indexes: [10, 11, 2, 3],
            chunkSize: 4,
            delayMs: 100,
            prefetchRange,
            isCurrent: () => true
        });
        expect(prefetchRange).toHaveBeenCalledExactlyOnceWith({
            requestId: 'request-1',
            ranges: [
                { startIndex: 2, endIndex: 3 },
                { startIndex: 10, endIndex: 11 }
            ]
        });
    });

    it('prefetches chunks sequentially with a delay between them', async () => {
        const prefetchRange = vi.fn().mockResolvedValue(undefined);
        const promise = prefetchInChunks({
            requestId: 'request-1',
            indexes: [0, 1, 2],
            chunkSize: 2,
            delayMs: 100,
            prefetchRange,
            isCurrent: () => true
        });

        await vi.waitFor(() => expect(prefetchRange).toHaveBeenCalledTimes(1));
        expect(prefetchRange).toHaveBeenCalledWith({
            requestId: 'request-1',
            ranges: [{ startIndex: 0, endIndex: 1 }]
        });

        await vi.advanceTimersByTimeAsync(100);
        await vi.waitFor(() => expect(prefetchRange).toHaveBeenCalledTimes(2));
        await promise;
    });

    it('stops before the next chunk when the schedule is replaced', async () => {
        const prefetchRange = vi.fn().mockResolvedValue(undefined);
        let current = true;
        const promise = prefetchInChunks({
            requestId: 'request-1',
            indexes: [0, 1, 2],
            chunkSize: 2,
            delayMs: 100,
            prefetchRange,
            isCurrent: () => current
        });

        await vi.waitFor(() => expect(prefetchRange).toHaveBeenCalledOnce());
        current = false;
        await vi.advanceTimersByTimeAsync(100);
        await promise;

        expect(prefetchRange).toHaveBeenCalledOnce();
    });
});
