import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { useTickDetails } from './useTickDetails.svelte';

describe('useTickDetails', () => {
    const query = {
        data: { recording_id: 'recording-1', seq_number: 0, timestamp_ns: 1000, channels: {} },
        isSuccess: true
    } satisfies Partial<CreateQueryResult<TickDetailView, Error>>;

    // The hook hands createQuery a thunk that resolves the query options for the
    // current getter values; capture it to assert the request it would issue.
    let queryOptionsThunk: () => { queryKey: unknown; enabled: boolean };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query as unknown as CreateQueryResult<TickDetailView, Error>;
        });
    });

    it('exposes the tick details query', () => {
        const { tickDetails } = useTickDetails({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'sequence-1',
            getSeqNumber: () => 2
        });

        expect(tickDetails).toBe(query);
    });

    it('requests tick details for the given dataset, sequence, and tick position', () => {
        useTickDetails({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'sequence-1',
            getSeqNumber: () => 2
        });

        expect(queryOptionsThunk().queryKey).toContainEqual(
            expect.objectContaining({
                path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1', seq_number: 2 }
            })
        );
    });

    it('enables the query only when both the dataset and sequence ids are present', () => {
        useTickDetails({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'sequence-1',
            getSeqNumber: () => 0
        });

        expect(queryOptionsThunk().enabled).toBe(true);
    });

    it.each([
        { label: 'dataset id', datasetId: '', sequenceId: 'sequence-1' },
        { label: 'sequence id', datasetId: 'dataset-1', sequenceId: '' }
    ])('disables the query when the $label is missing', ({ datasetId, sequenceId }) => {
        useTickDetails({
            getDatasetId: () => datasetId,
            getSequenceId: () => sequenceId,
            getSeqNumber: () => 0
        });

        expect(queryOptionsThunk().enabled).toBe(false);
    });
});
