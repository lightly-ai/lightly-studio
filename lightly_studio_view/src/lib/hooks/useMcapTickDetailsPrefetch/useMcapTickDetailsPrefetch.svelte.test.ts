import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Harness from './UseMcapTickDetailsPrefetchHarness.svelte';
import { useMcapTickDetailsPrefetch } from './useMcapTickDetailsPrefetch.svelte';

const mocks = vi.hoisted(() => ({
    cancel: vi.fn(),
    prefetchRanges: vi.fn(),
    onStateChange: undefined as
        | ((completed: ReadonlySet<number>, errors: ReadonlyMap<number, unknown>) => void)
        | undefined,
    createExecutor: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({})
}));
vi.mock('./createMcapTickPrefetchExecutor', () => ({
    createMcapTickPrefetchExecutor: mocks.createExecutor
}));

describe('useMcapTickDetailsPrefetch', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.onStateChange = undefined;
        mocks.createExecutor.mockImplementation((params) => {
            mocks.onStateChange = params.onStateChange;
            return {
                cancel: mocks.cancel,
                prefetchRanges: mocks.prefetchRanges
            };
        });
    });

    it('forwards range requests and exposes executor state', () => {
        let result: ReturnType<typeof useMcapTickDetailsPrefetch> | undefined;
        render(Harness, { props: { ticks: [], ranges: [], onReady: (value) => (result = value) } });
        flushSync();

        const error = new Error('prefetch failed');
        mocks.onStateChange?.(new Set([1, 2]), new Map([[4, error]]));
        flushSync();

        expect(result?.bufferedRanges).toEqual([{ startIndex: 1, endIndex: 2 }]);
        expect(result?.errors.get(4)).toBe(error);
    });

    it('exposes the executor controls', async () => {
        let result: ReturnType<typeof useMcapTickDetailsPrefetch> | undefined;
        render(Harness, { props: { ticks: [], ranges: [], onReady: (value) => (result = value) } });
        flushSync();

        await result?.prefetchRanges({ requestId: 'request-1', ranges: [] });
        result?.cancel();

        expect(mocks.prefetchRanges).toHaveBeenCalledWith({
            requestId: 'request-1',
            ranges: []
        });
        expect(mocks.cancel).toHaveBeenCalledOnce();
    });
});
