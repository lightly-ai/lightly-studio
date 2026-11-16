import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import Harness from './UseMcapTickPrefetchSchedulerHarness.svelte';
import type { useMcapTickPrefetchScheduler } from './useMcapTickPrefetchScheduler.svelte';

const { prefetchRanges, cancel, errors } = vi.hoisted(() => ({
    prefetchRanges: vi.fn().mockResolvedValue(undefined),
    cancel: vi.fn(),
    errors: new Map<number, unknown>()
}));

vi.mock('./useMcapTickDetailsPrefetch.svelte', () => ({
    useMcapTickDetailsPrefetch: () => ({
        prefetchRanges,
        cancel,
        errors,
        bufferedRanges: []
    })
}));

const ticks: TickView[] = Array.from({ length: 5 }, (_, seq_number) => ({
    seq_number,
    timestamp_ns: null
}));

describe('useMcapTickPrefetchScheduler', () => {
    afterEach(() => vi.useRealTimers());
    beforeEach(() => {
        vi.useFakeTimers();
        vi.clearAllMocks();
        errors.clear();
    });

    it('stops delayed chunks when the caller explicitly cancels buffering', async () => {
        let stop: (() => void) | undefined;
        render(Harness, {
            props: {
                ticks,
                ranges: [{ startIndex: 0, endIndex: 4 }],
                onReady: (value) => {
                    stop = value.cancel;
                }
            }
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledOnce());
        stop?.();
        await vi.advanceTimersByTimeAsync(500);
        expect(cancel).toHaveBeenCalledOnce();
        expect(prefetchRanges).toHaveBeenCalledOnce();
    });

    it('continues buffering earlier ticks after reaching the end of the sequence', async () => {
        render(Harness, {
            props: {
                ticks,
                ranges: [
                    { startIndex: 3, endIndex: 4 },
                    { startIndex: 0, endIndex: 2 }
                ],
                onReady: () => undefined
            }
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledOnce());
        expect(prefetchRanges).toHaveBeenNthCalledWith(1, {
            requestId: 'test',
            ranges: [{ startIndex: 3, endIndex: 4 }]
        });

        await vi.advanceTimersByTimeAsync(200);

        expect(prefetchRanges).toHaveBeenNthCalledWith(2, {
            requestId: 'test',
            ranges: [{ startIndex: 0, endIndex: 1 }]
        });
        expect(prefetchRanges).toHaveBeenNthCalledWith(3, {
            requestId: 'test',
            ranges: [{ startIndex: 2, endIndex: 2 }]
        });
    });

    it('retries only failed ticks while preserving the buffering session', async () => {
        let scheduler: ReturnType<typeof useMcapTickPrefetchScheduler> | undefined;
        render(Harness, {
            props: {
                ticks,
                ranges: [],
                onReady: (value) => (scheduler = value)
            }
        });
        flushSync();
        errors.set(1, new Error('Failed to load'));
        errors.set(4, new Error('Failed to load'));
        let finishRetry!: () => void;
        prefetchRanges.mockReturnValueOnce(new Promise<void>((resolve) => (finishRetry = resolve)));

        const pending = scheduler?.retryFailed();
        await scheduler?.retryFailed();

        expect(scheduler?.isRetrying).toBe(true);
        expect(prefetchRanges).toHaveBeenCalledExactlyOnceWith({
            requestId: 'test',
            ranges: [
                { startIndex: 1, endIndex: 1 },
                { startIndex: 4, endIndex: 4 }
            ]
        });
        finishRetry();
        await pending;
        expect(scheduler?.isRetrying).toBe(false);
    });

    it('keeps the session when playback ranges advance', async () => {
        const view = render(Harness, {
            props: { ticks, ranges: [{ startIndex: 0, endIndex: 1 }], onReady: () => undefined }
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledOnce());
        expect(cancel).not.toHaveBeenCalled();

        await view.rerender({
            ticks,
            ranges: [{ startIndex: 2, endIndex: 3 }],
            onReady: () => undefined
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledTimes(2));

        expect(cancel).not.toHaveBeenCalled();
        expect(prefetchRanges).toHaveBeenNthCalledWith(2, {
            requestId: 'test',
            ranges: [{ startIndex: 2, endIndex: 3 }]
        });
    });

    it('keeps loading an earlier plan when playback moves the look-ahead window', async () => {
        const view = render(Harness, {
            props: {
                ticks,
                ranges: [{ startIndex: 0, endIndex: 4 }],
                onReady: () => undefined
            }
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledOnce());

        await view.rerender({
            ticks,
            ranges: [{ startIndex: 1, endIndex: 4 }],
            onReady: () => undefined
        });
        flushSync();
        await vi.advanceTimersByTimeAsync(100);

        expect(prefetchRanges).toHaveBeenCalledWith({
            requestId: 'test',
            ranges: [{ startIndex: 2, endIndex: 3 }]
        });
    });

    it('switches buffering sessions without clearing completed ranges', async () => {
        const view = render(Harness, {
            props: { ticks, ranges: [{ startIndex: 0, endIndex: 4 }], onReady: () => undefined }
        });
        flushSync();
        await vi.waitFor(() => expect(prefetchRanges).toHaveBeenCalledOnce());

        await view.rerender({
            ticks,
            ranges: [{ startIndex: 0, endIndex: 1 }],
            requestId: 'window',
            onReady: () => undefined
        });
        flushSync();

        expect(cancel).not.toHaveBeenCalled();
        expect(prefetchRanges).toHaveBeenLastCalledWith({
            requestId: 'window',
            ranges: [{ startIndex: 0, endIndex: 1 }]
        });
    });
});
