import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import type { useTickDetails } from './useTickDetails';
import UseTickDetailsHarness from './UseTickDetailsHarness.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({ getTickDetails: vi.fn() }));

describe('useTickDetails', () => {
    const data = {
        recording_id: 'recording-1',
        seq_number: 0,
        timestamp_ns: 1000,
        camera_channels: {},
        lidar_channels: {},
        annotations: []
    } satisfies TickDetailView;
    const query = { data, isSuccess: true } satisfies Partial<
        CreateQueryResult<TickDetailView, Error>
    >;
    const path = { dataset_id: 'dataset-1', sequence_id: 'sequence-1', seq_number: 2 };

    // The thunk the hook hands to createQuery; invoking it yields the resolved
    // query options for the current getter values.
    let queryOptionsThunk: () => {
        queryKey: unknown[];
        queryFn: (context: { signal: AbortSignal }) => Promise<TickDetailView>;
        enabled: boolean;
        placeholderData: (previous: TickDetailView | undefined) => TickDetailView | undefined;
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.mocked(getTickDetails).mockResolvedValue({ data } as unknown as Awaited<
            ReturnType<typeof getTickDetails>
        >);
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return query as unknown as CreateQueryResult<TickDetailView, Error>;
        });
    });

    const renderHook = (props: {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        targetFrameId?: string;
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

    it('requests tick details for the given dataset, sequence, and tick position', async () => {
        renderHook({ datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 2 });
        const signal = new AbortController().signal;

        await expect(queryOptionsThunk().queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenCalledExactlyOnceWith({
            path,
            signal,
            throwOnError: true
        });
    });

    it('requests the cuboids in the target frame when one is given', async () => {
        renderHook({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 2,
            targetFrameId: 'map'
        });
        const signal = new AbortController().signal;

        await expect(queryOptionsThunk().queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenCalledExactlyOnceWith({
            path,
            query: { target_frame_id: 'map' },
            signal,
            throwOnError: true
        });
    });

    it('keys the query by the target frame', () => {
        renderHook({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 2,
            targetFrameId: 'map'
        });

        expect(queryOptionsThunk().queryKey).toEqual([
            expect.objectContaining({ path, query: { target_frame_id: 'map' } })
        ]);
    });

    it('loads the cuboids in their own frames when they cannot be mapped', async () => {
        renderHook({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 2,
            targetFrameId: 'map'
        });
        vi.mocked(getTickDetails).mockRejectedValueOnce(new Error('No transform'));
        const signal = new AbortController().signal;

        await expect(queryOptionsThunk().queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenLastCalledWith({ path, signal, throwOnError: true });
    });

    it('does not retry without a target frame when the request is aborted', async () => {
        renderHook({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 2,
            targetFrameId: 'map'
        });
        const controller = new AbortController();
        controller.abort();
        vi.mocked(getTickDetails).mockRejectedValueOnce(new Error('Aborted'));

        await expect(queryOptionsThunk().queryFn({ signal: controller.signal })).rejects.toThrow(
            'Aborted'
        );
        expect(getTickDetails).toHaveBeenCalledOnce();
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
