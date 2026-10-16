import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/svelte-query';
import { createMcapTickPrefetchExecutor } from './createMcapTickPrefetchExecutor';
import { prefetchMcapTick } from './prefetchMcapTick';

vi.mock('./prefetchMcapTick', () => ({ prefetchMcapTick: vi.fn() }));
const prefetchMock = vi.mocked(prefetchMcapTick);
const ticks = Array.from({ length: 6 }, (_, seq_number) => ({ seq_number, timestamp_ns: null }));

function createExecutor(onStateChange = vi.fn()) {
    return createMcapTickPrefetchExecutor({
        client: {} as QueryClient,
        getDatasetId: () => 'dataset-1',
        getSequenceId: () => 'sequence-1',
        getDisplayFrameId: () => undefined,
        getTicks: () => ticks,
        onStateChange
    });
}

describe('createMcapTickPrefetchExecutor', () => {
    beforeEach(() => {
        prefetchMock.mockReset();
    });

    it('shares overlapping pending work and skips completed ticks in the same session', async () => {
        let complete!: () => void;
        prefetchMock.mockImplementation(() => new Promise<void>((resolve) => (complete = resolve)));
        const executor = createExecutor();
        const request = { requestId: 'session-1', ranges: [{ startIndex: 0, endIndex: 0 }] };
        const first = executor.prefetchRanges(request);
        let secondFinished = false;
        const second = executor.prefetchRanges(request).then(() => (secondFinished = true));
        await Promise.resolve();
        expect(secondFinished).toBe(false);
        expect(prefetchMock).toHaveBeenCalledOnce();

        complete();
        await Promise.all([first, second]);
        await executor.prefetchRanges(request);
        expect(prefetchMock).toHaveBeenCalledOnce();
    });

    it('discards queued work and ignores old completions after switching sessions', async () => {
        const completions: Array<() => void> = [];
        prefetchMock.mockImplementation(
            () => new Promise<void>((resolve) => completions.push(resolve))
        );
        const onStateChange = vi.fn();
        const executor = createExecutor(onStateChange);
        const oldRequest = executor.prefetchRanges({
            requestId: 'old',
            ranges: [{ startIndex: 0, endIndex: 5 }]
        });
        expect(prefetchMock).toHaveBeenCalledTimes(4);
        const newRequest = executor.prefetchRanges({
            requestId: 'new',
            ranges: [{ startIndex: 5, endIndex: 5 }]
        });
        await oldRequest;
        onStateChange.mockClear();
        for (const complete of completions.slice(0, 4)) complete();
        await Promise.resolve();
        expect(onStateChange).not.toHaveBeenCalled();
        expect(prefetchMock).toHaveBeenCalledTimes(5);

        completions[4]();
        await newRequest;
        expect(onStateChange).toHaveBeenLastCalledWith(new Set([5]), new Map());
        executor.cancel();
        expect(onStateChange).toHaveBeenLastCalledWith(new Set(), new Map());
    });

    it('keeps completed ticks when switching buffering sessions', async () => {
        prefetchMock.mockResolvedValue(undefined);
        const onStateChange = vi.fn();
        const executor = createExecutor(onStateChange);

        await executor.prefetchRanges({
            requestId: 'old',
            ranges: [{ startIndex: 0, endIndex: 1 }]
        });
        await executor.prefetchRanges({
            requestId: 'new',
            ranges: [{ startIndex: 2, endIndex: 3 }]
        });

        expect(onStateChange).toHaveBeenLastCalledWith(new Set([0, 1, 2, 3]), new Map());
    });
});
