import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { fetchMergedCloudPointFrame } from './fetchMergedCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame } from './types';

vi.mock('./fetchCloudPointFrame', () => ({
    fetchCloudPointFrame: vi.fn()
}));
vi.mock('./mergeCloudPointFrames', () => ({
    mergeCloudPointFrames: vi.fn()
}));

describe('fetchMergedCloudPointFrame', () => {
    beforeEach(() => vi.clearAllMocks());

    it('fetches every channel with the same frame options and merges the results', async () => {
        const first = { frameId: 'first' } as unknown as CloudPointFrame;
        const second = { frameId: 'second' } as unknown as CloudPointFrame;
        const merged = { frameId: 'first,second' } as unknown as CloudPointFrame;
        vi.mocked(fetchCloudPointFrame).mockResolvedValueOnce(first).mockResolvedValueOnce(second);
        vi.mocked(mergeCloudPointFrames).mockReturnValue(merged);
        const signal = new AbortController().signal;

        const result = await fetchMergedCloudPointFrame({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channels: [
                { channelId: 1, timestampNs: '100' },
                { channelId: 2, timestampNs: '200' }
            ],
            displayFrameId: 'base_link',
            signal
        });

        expect(fetchCloudPointFrame).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel: { channelId: 1, timestampNs: '100' },
            displayFrameId: 'base_link',
            signal
        });
        expect(fetchCloudPointFrame).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel: { channelId: 2, timestampNs: '200' },
            displayFrameId: 'base_link',
            signal
        });
        expect(mergeCloudPointFrames).toHaveBeenCalledWith([first, second]);
        expect(result).toBe(merged);
    });

    it('rejects empty channel lists before starting a request', async () => {
        await expect(
            fetchMergedCloudPointFrame({
                datasetId: 'dataset-1',
                recordingId: 'recording-1',
                channels: []
            })
        ).rejects.toThrow('No point cloud channels to load.');
        expect(fetchCloudPointFrame).not.toHaveBeenCalled();
    });
});
