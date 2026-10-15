import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import Harness from './UseMcapTickPrefetchSchedulerHarness.svelte';

const { prefetchRanges, cancel } = vi.hoisted(() => ({
    prefetchRanges: vi.fn().mockResolvedValue(undefined),
    cancel: vi.fn()
}));

vi.mock('./useMcapTickDetailsPrefetch.svelte', () => ({
    useMcapTickDetailsPrefetch: () => ({
        prefetchRanges,
        cancel,
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

    it('cancels the old queue when the buffering session changes', async () => {
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

        expect(cancel).toHaveBeenCalledOnce();
        expect(prefetchRanges).toHaveBeenLastCalledWith({
            requestId: 'window',
            ranges: [{ startIndex: 0, endIndex: 1 }]
        });
    });
});
