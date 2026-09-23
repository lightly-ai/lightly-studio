import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as svelteQueryGen from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import type { useTickDetails } from './useTickDetails';
import UseTickDetailsHarness from './UseTickDetailsHarness.svelte';

describe('useTickDetails', () => {
    // Sentinel that stands in for the generated query options, so we can assert
    // the hook merges its own `enabled` flag onto them.
    const baseOptions = { queryKey: ['tick-details'], queryFn: vi.fn() };
    const query = {
        data: { recording_id: 'recording-1', seq_number: 0, timestamp_ns: 1000, channels: {} },
        isSuccess: true
    } satisfies Partial<CreateQueryResult<TickDetailView, Error>>;

    // The thunk the hook hands to createQuery; invoking it yields the resolved
    // query options for the current getter values.
    let queryOptionsThunk: () => { enabled: boolean };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(svelteQueryGen, 'getTickDetailsOptions').mockReturnValue(
            baseOptions as unknown as ReturnType<typeof svelteQueryGen.getTickDetailsOptions>
        );
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query as unknown as CreateQueryResult<TickDetailView, Error>;
        });
    });

    const renderHook = (props: { datasetId: string; sequenceId: string; seqNumber: number }) => {
        let result: ReturnType<typeof useTickDetails> | undefined;
        render(UseTickDetailsHarness, {
            ...props,
            onReady: (hookResult) => {
                result = hookResult;
            }
        });
        flushSync();
        if (!result) throw new Error('useTickDetails did not initialize');
        return result;
    };

    it('exposes the tick details query', () => {
        const { tickDetails } = renderHook({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 2
        });

        expect(tickDetails).toBe(query);
    });

    it('requests tick details for the given dataset, sequence, and tick position', () => {
        renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 2 });
        queryOptionsThunk();

        expect(svelteQueryGen.getTickDetailsOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1', seq_number: 2 }
        });
    });

    it('enables the query only when both the dataset and sequence ids are present', () => {
        renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 0 });
        expect(queryOptionsThunk().enabled).toBe(true);
    });

    it.each([
        { label: 'dataset id', datasetId: '', sequenceId: 'sequence-1' },
        { label: 'sequence id', datasetId: 'dataset-1', sequenceId: '' }
    ])('disables the query when the $label is missing', ({ datasetId, sequenceId }) => {
        renderHook({ datasetId, sequenceId, seqNumber: 0 });
        expect(queryOptionsThunk().enabled).toBe(false);
    });
});
