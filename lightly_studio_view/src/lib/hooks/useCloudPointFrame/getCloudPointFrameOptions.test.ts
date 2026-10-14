import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchMergedCloudPointFrame } from './fetchMergedCloudPointFrame';
import { getCloudPointFrameOptions } from './getCloudPointFrameOptions';
import type { CloudPointFrame } from './types';

vi.mock('./fetchMergedCloudPointFrame', () => ({
    fetchMergedCloudPointFrame: vi.fn()
}));

const params = {
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channels: [{ channelId: 3, timestampNs: '100' }],
    displayFrameId: 'base_link'
};

describe('getCloudPointFrameOptions', () => {
    beforeEach(() => vi.clearAllMocks());

    it('builds a stable cache key from all frame parameters', () => {
        const options = getCloudPointFrameOptions(params);

        expect(options.queryKey).toEqual([
            'cloud-point-frame',
            'dataset-1',
            'recording-1',
            [{ channelId: 3, timestampNs: '100' }],
            'base_link'
        ]);
    });

    it('fetches the requested frame with the query signal', async () => {
        const frame = { frameId: 'frame-1' } as unknown as CloudPointFrame;
        vi.mocked(fetchMergedCloudPointFrame).mockResolvedValue(frame);
        const signal = new AbortController().signal;

        const result = await getCloudPointFrameOptions(params).queryFn({ signal });

        expect(fetchMergedCloudPointFrame).toHaveBeenCalledWith({ ...params, signal });
        expect(result).toBe(frame);
    });

    it('retries without a target frame when transform data is unavailable', async () => {
        const frame = { frameId: 'sensor-frame' } as unknown as CloudPointFrame;
        vi.mocked(fetchMergedCloudPointFrame)
            .mockRejectedValueOnce({ detail: { type: 'transform_unavailable' } })
            .mockResolvedValueOnce(frame);
        const signal = new AbortController().signal;

        const result = await getCloudPointFrameOptions(params).queryFn({ signal });

        expect(fetchMergedCloudPointFrame).toHaveBeenNthCalledWith(1, { ...params, signal });
        expect(fetchMergedCloudPointFrame).toHaveBeenNthCalledWith(2, {
            ...params,
            displayFrameId: undefined,
            signal
        });
        expect(result).toBe(frame);
    });
});
