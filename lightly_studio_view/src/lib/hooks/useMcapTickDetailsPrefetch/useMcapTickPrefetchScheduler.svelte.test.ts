import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import Harness from './UseMcapTickPrefetchSchedulerHarness.svelte';

const { prefetchRanges, cancel, setErrors } = vi.hoisted(() => ({
    prefetchRanges: vi.fn().mockResolvedValue(undefined),
    cancel: vi.fn(),
    setErrors: vi.fn<(errors: Map<number, unknown>) => void>()
}));

vi.mock('./useMcapTickDetailsPrefetch.svelte', () => ({
    useMcapTickDetailsPrefetch: () => {
        let errors = $state(new Map<number, unknown>());
        setErrors.mockImplementation((nextErrors) => (errors = nextErrors));
        return {
            prefetchRanges,
            cancel,
            bufferedRanges: [],
            get errors() {
                return errors;
            }
        };
    }
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

    it('retries a failed tick until buffering succeeds without advancing playback', async () => {
        render(Harness, {
            props: { ticks, ranges: [{ startIndex: 0, endIndex: 1 }], onReady: () => undefined }
        });
        flushSync();
        setErrors(new Map([[1, new Error('Temporary loading failure')]]));
        flushSync();

        await vi.advanceTimersByTimeAsync(2000);
        expect(prefetchRanges).toHaveBeenCalledTimes(3);
        expect(prefetchRanges).toHaveBeenLastCalledWith({
            requestId: 'test',
            ranges: [{ startIndex: 1, endIndex: 1 }]
        });

        setErrors(new Map());
        flushSync();
        await vi.advanceTimersByTimeAsync(2000);
        expect(prefetchRanges).toHaveBeenCalledTimes(3);
    });

    it('stops retrying failed ticks when buffering is cancelled', async () => {
        let stop: (() => void) | undefined;
        render(Harness, {
            props: {
                ticks,
                ranges: [{ startIndex: 0, endIndex: 1 }],
                onReady: (value) => (stop = value.cancel)
            }
        });
        flushSync();
        setErrors(new Map([[1, new Error('Temporary loading failure')]]));
        flushSync();
        stop?.();
        flushSync();

        await vi.advanceTimersByTimeAsync(2000);
        expect(prefetchRanges).toHaveBeenCalledOnce();
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
