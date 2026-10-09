import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import type { useTickDetails } from './useTickDetails';
import UseTickDetailsHarness from './UseTickDetailsHarness.svelte';

describe('useTickDetails', () => {
    const data = {
        sample_id: 'sample-1',
        collection_id: 'collection-1',
        recording_id: 'recording-1',
        seq_number: 0,
        timestamp_ns: 1000,
        camera_channels: {},
        lidar_channels: {},
        annotations: [],
        tags: []
    } satisfies TickDetailView;
    const query = { data, isSuccess: true } satisfies Partial<
        CreateQueryResult<TickDetailView, Error>
    >;

    let queryOptionsThunk: () => {
        enabled: boolean;
        placeholderData: (previous: TickDetailView | undefined) => TickDetailView | undefined;
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query as unknown as CreateQueryResult<TickDetailView, Error>;
        });
    });

    const renderHook = (props: {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        displayFrameId?: string;
    }) => {
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

    it('keeps the previous tick details while the next tick loads', () => {
        renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 2 });

        expect(queryOptionsThunk().placeholderData(data)).toBe(data);
        expect(queryOptionsThunk().placeholderData(undefined)).toBeUndefined();
    });
});
