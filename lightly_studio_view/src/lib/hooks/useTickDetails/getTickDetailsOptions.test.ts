import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import { getTickDetailsOptions } from './getTickDetailsOptions';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getTickDetails: vi.fn()
}));

const params = {
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 4,
    displayFrameId: 'base_link'
};

describe('getTickDetailsOptions', () => {
    beforeEach(() => vi.clearAllMocks());

    it('builds the cache key with the optional target frame', () => {
        const [key] = getTickDetailsOptions(params).queryKey as [Record<string, unknown>];

        expect(key).toMatchObject({
            _id: 'getTickDetails',
            path: {
                dataset_id: 'dataset-1',
                sequence_id: 'sequence-1',
                seq_number: 4
            },
            query: { target_frame_id: 'base_link' }
        });
    });

    it('omits the target frame when it is not provided', () => {
        const [key] = getTickDetailsOptions({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 4
        }).queryKey as [Record<string, unknown>];

        expect(key).not.toHaveProperty('query');
    });

    it('requests tick details in the target frame', async () => {
        const data = { annotations: [] };
        vi.mocked(getTickDetails).mockResolvedValue({ data } as never);
        const signal = new AbortController().signal;

        const result = await getTickDetailsOptions(params).queryFn({ signal });

        expect(getTickDetails).toHaveBeenCalledWith({
            path: {
                dataset_id: 'dataset-1',
                sequence_id: 'sequence-1',
                seq_number: 4
            },
            query: { target_frame_id: 'base_link' },
            signal,
            throwOnError: true
        });
        expect(result).toBe(data);
    });

    it('retries without a target frame when the transform is unavailable', async () => {
        const data = { annotations: [] };
        vi.mocked(getTickDetails)
            .mockRejectedValueOnce({ detail: { type: 'transform_unavailable' } })
            .mockResolvedValueOnce({ data } as never);
        const signal = new AbortController().signal;

        const result = await getTickDetailsOptions(params).queryFn({ signal });

        expect(getTickDetails).toHaveBeenNthCalledWith(2, {
            path: {
                dataset_id: 'dataset-1',
                sequence_id: 'sequence-1',
                seq_number: 4
            },
            signal,
            throwOnError: true
        });
        expect(result).toBe(data);
    });

    it('does not retry unrelated errors', async () => {
        const error = new Error('request failed');
        vi.mocked(getTickDetails).mockRejectedValue(error);

        await expect(
            getTickDetailsOptions(params).queryFn({ signal: new AbortController().signal })
        ).rejects.toBe(error);
        expect(getTickDetails).toHaveBeenCalledTimes(1);
    });
});
