import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult, QueryClient } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as svelteQueryGen from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickListView } from '$lib/api/lightly_studio_local/types.gen';
import type { useMcapSequenceTicks } from './useMcapSequenceTicks.svelte';
import Harness from './UseMcapSequenceTicksHarness.svelte';

describe('useMcapSequenceTicks', () => {
    const invalidateQueries = vi.fn();
    const query = { data: { ticks: [] } } as unknown as CreateQueryResult<TickListView, Error>;
    const baseOptions = { queryKey: ['ticks'], queryFn: vi.fn() };
    let queryOptionsThunk: () => { enabled: boolean };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue({
            invalidateQueries
        } as unknown as QueryClient);
        vi.spyOn(svelteQueryGen, 'getTicksOptions').mockReturnValue(
            baseOptions as unknown as ReturnType<typeof svelteQueryGen.getTicksOptions>
        );
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query;
        });
    });

    const renderHook = (datasetId: string, sequenceId: string) => {
        let result: ReturnType<typeof useMcapSequenceTicks> | undefined;
        render(Harness, {
            datasetId,
            sequenceId,
            onReady: (value: ReturnType<typeof useMcapSequenceTicks>) => (result = value)
        });
        flushSync();
        if (!result) throw new Error('useMcapSequenceTicks did not initialize');
        return result;
    };

    it('loads all ticks for the sequence when both ids are present', () => {
        const result = renderHook('dataset-1', 'sequence-1');

        expect(result.ticks).toBe(query);
        expect(queryOptionsThunk().enabled).toBe(true);
        expect(svelteQueryGen.getTicksOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' }
        });
    });

    it.each([
        { datasetId: '', sequenceId: 'sequence-1' },
        { datasetId: 'dataset-1', sequenceId: '' }
    ])('does not load ticks without both ids', ({ datasetId, sequenceId }) => {
        renderHook(datasetId, sequenceId);

        expect(queryOptionsThunk().enabled).toBe(false);
    });

    it('invalidates the sequence tick query when refetched', () => {
        const { refetch } = renderHook('dataset-1', 'sequence-1');

        refetch();

        expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: baseOptions.queryKey });
    });
});
