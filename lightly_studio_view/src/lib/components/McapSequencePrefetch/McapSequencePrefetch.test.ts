import { render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import McapSequencePrefetch from './McapSequencePrefetch.svelte';

const { useScheduler } = vi.hoisted(() => ({
    useScheduler: vi.fn()
}));

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({
        summary: {
            data: { reference_frames: [{ name: 'map' }, { name: 'CABIN' }] }
        }
    })
}));

vi.mock('$lib/hooks/useMcapSequenceTicks/useMcapSequenceTicks.svelte', () => ({
    useMcapSequenceTicks: () => ({
        ticks: {
            data: {
                ticks: Array.from({ length: 60 }, (_, seq_number) => ({ seq_number }))
            }
        }
    })
}));

vi.mock('$lib/hooks/useMcapTickDetailsPrefetch/useMcapTickPrefetchScheduler.svelte', () => ({
    useMcapTickPrefetchScheduler: useScheduler
}));

describe('McapSequencePrefetch', () => {
    let runIdleCallback: (() => void) | undefined;

    beforeEach(() => {
        vi.clearAllMocks();
        runIdleCallback = undefined;
        Object.defineProperty(window, 'requestIdleCallback', {
            configurable: true,
            value: (callback: () => void) => {
                runIdleCallback = callback;
                return 1;
            }
        });
    });

    it('starts prefetching the first 50 ticks for the sequence when idle', async () => {
        render(McapSequencePrefetch, {
            props: { datasetId: 'dataset-1', sequenceId: 'sequence-1' }
        });
        expect(useScheduler).toHaveBeenCalledOnce();
        const initialParams = useScheduler.mock.calls[0][0];
        expect(initialParams.getEnabled()).toBe(false);

        runIdleCallback?.();
        await vi.waitFor(() => expect(initialParams.getEnabled()).toBe(true));

        expect(useScheduler).toHaveBeenCalledWith(
            expect.objectContaining({
                getDatasetId: expect.any(Function),
                getSequenceId: expect.any(Function),
                getTicks: expect.any(Function),
                getRanges: expect.any(Function)
            })
        );
        const params = useScheduler.mock.calls[0][0];
        expect(params.getDatasetId()).toBe('dataset-1');
        expect(params.getSequenceId()).toBe('sequence-1');
        expect(params.getDisplayFrameId()).toBe('CABIN');
        expect(params.getRequestId()).toBe('grid/dataset-1/sequence-1/CABIN');
        expect(params.getRanges()).toEqual([{ startIndex: 0, endIndex: 49 }]);
        expect(params.getTicks()).toHaveLength(60);
    });
});
