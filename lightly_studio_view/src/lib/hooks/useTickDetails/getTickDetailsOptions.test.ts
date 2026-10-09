import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { getTickDetailsOptions } from './getTickDetailsOptions';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({ getTickDetails: vi.fn() }));

describe('getTickDetailsOptions', () => {
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
    const defaultOptions = { datasetId: 'dataset-1', sequenceId: 'sequence-1', seqNumber: 2 };
    const path = { dataset_id: 'dataset-1', sequence_id: 'sequence-1', seq_number: 2 };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.mocked(getTickDetails).mockResolvedValue({ data } as unknown as Awaited<
            ReturnType<typeof getTickDetails>
        >);
    });

    it('requests tick details for the given dataset, sequence, and tick position', async () => {
        const { queryFn } = getTickDetailsOptions(defaultOptions);
        const signal = new AbortController().signal;

        await expect(queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenCalledExactlyOnceWith({
            path,
            signal,
            throwOnError: true
        });
    });

    it('requests the cuboids in the target frame when one is given', async () => {
        const { queryFn } = getTickDetailsOptions({ ...defaultOptions, displayFrameId: 'map' });
        const signal = new AbortController().signal;

        await expect(queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenCalledExactlyOnceWith({
            path,
            query: { target_frame_id: 'map' },
            signal,
            throwOnError: true
        });
    });

    it('keys the query by the target frame', () => {
        const { queryKey } = getTickDetailsOptions({ ...defaultOptions, displayFrameId: 'map' });

        expect(queryKey).toEqual([
            expect.objectContaining({ path, query: { target_frame_id: 'map' } })
        ]);
    });

    it('loads the cuboids in their own frames when they cannot be mapped to the target', async () => {
        const { queryFn } = getTickDetailsOptions({ ...defaultOptions, displayFrameId: 'map' });
        vi.mocked(getTickDetails).mockRejectedValueOnce({
            detail: { type: 'transform_unavailable', message: 'No transform' }
        });
        const signal = new AbortController().signal;

        await expect(queryFn({ signal })).resolves.toBe(data);
        expect(getTickDetails).toHaveBeenLastCalledWith({ path, signal, throwOnError: true });
    });

    it('does not retry on errors other than transform_unavailable', async () => {
        const { queryFn } = getTickDetailsOptions({ ...defaultOptions, displayFrameId: 'map' });
        vi.mocked(getTickDetails).mockRejectedValueOnce({ detail: 'Recording was not found.' });

        await expect(queryFn({ signal: new AbortController().signal })).rejects.toEqual({
            detail: 'Recording was not found.'
        });
        expect(getTickDetails).toHaveBeenCalledOnce();
    });

    it('does not retry when the request is aborted', async () => {
        const { queryFn } = getTickDetailsOptions({ ...defaultOptions, displayFrameId: 'map' });
        const controller = new AbortController();
        controller.abort();
        vi.mocked(getTickDetails).mockRejectedValueOnce(new Error('Aborted'));

        await expect(queryFn({ signal: controller.signal })).rejects.toThrow('Aborted');
        expect(getTickDetails).toHaveBeenCalledOnce();
    });
});
