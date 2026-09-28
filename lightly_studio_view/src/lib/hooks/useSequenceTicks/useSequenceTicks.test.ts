import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as svelteQueryGen from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickListView } from '$lib/api/lightly_studio_local/types.gen';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import type { useSequenceTicks } from './useSequenceTicks';
import UseSequenceTicksHarness from './UseSequenceTicksHarness.svelte';

describe('useSequenceTicks', () => {
    // Sentinel that stands in for the generated query options, so we can assert
    // the hook merges its own `enabled` flag onto them.
    const baseOptions = { queryKey: ['ticks'], queryFn: vi.fn() };
    const query = {
        data: { ticks: [{ seq_number: 0, timestamp_ns: 1000 }] },
        isSuccess: true
    } satisfies Partial<CreateQueryResult<TickListView, Error>>;

    // The thunk the hook hands to createQuery; invoking it yields the resolved
    // query options for the current getter values.
    let queryOptionsThunk: () => { enabled: boolean };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(svelteQueryGen, 'getTicksOptions').mockReturnValue(
            baseOptions as unknown as ReturnType<typeof svelteQueryGen.getTicksOptions>
        );
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query as unknown as CreateQueryResult<TickListView, Error>;
        });
    });

    const renderHook = (props: { datasetId: string; sequenceId: string }) => {
        let result: ReturnType<typeof useSequenceTicks> | undefined;
        render(UseSequenceTicksHarness, {
            ...props,
            onReady: (hookResult) => {
                result = hookResult;
            }
        });
        flushSync();
        if (!result) throw new Error('useSequenceTicks did not initialize');
        return result;
    };

    it('requests the ticks of the given dataset and sequence', () => {
        const { sequenceTicks } = renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1' });
        queryOptionsThunk();

        expect(sequenceTicks).toBe(query);
        expect(svelteQueryGen.getTicksOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' }
        });
    });

    it('enables the query only when both the dataset and sequence ids are present', () => {
        renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1' });
        expect(queryOptionsThunk().enabled).toBe(true);
    });

    it.each([
        { label: 'dataset id', datasetId: '', sequenceId: 'sequence-1' },
        { label: 'sequence id', datasetId: 'dataset-1', sequenceId: '' }
    ])('disables the query when the $label is missing', ({ datasetId, sequenceId }) => {
        renderHook({ datasetId, sequenceId });
        expect(queryOptionsThunk().enabled).toBe(false);
    });
});
