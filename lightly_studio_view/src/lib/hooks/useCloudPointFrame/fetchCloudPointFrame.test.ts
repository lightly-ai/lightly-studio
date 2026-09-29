import { describe, it, expect, vi, afterEach } from 'vitest';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { getPointCloud } from '$lib/api/lightly_studio_local';
import { parseCloudPointFrame } from './parseCloudPointFrame';
import type { CloudPointFrame } from './types';

vi.mock('./parseCloudPointFrame', () => ({ parseCloudPointFrame: vi.fn() }));
vi.mock('$lib/api/lightly_studio_local', () => ({ getPointCloud: vi.fn() }));

const defaultArgs = {
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channel: { channelId: 1, timestampNs: '100' }
};

describe('fetchCloudPointFrame', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('requests the channel as an arrow buffer and parses the response', async () => {
        const parsed = { frameId: 'frame-1' } as unknown as CloudPointFrame;
        const buffer = new ArrayBuffer(8);
        vi.mocked(getPointCloud).mockResolvedValue({
            data: buffer,
            response: { ok: true } as Response
        } as Awaited<ReturnType<typeof getPointCloud>>);
        vi.mocked(parseCloudPointFrame).mockResolvedValue(parsed);

        const signal = new AbortController().signal;
        const result = await fetchCloudPointFrame({ ...defaultArgs, signal });

        expect(getPointCloud).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', recording_id: 'recording-1' },
            query: { channel_id: 1, timestamp_ns: '100' },
            parseAs: 'arrayBuffer',
            signal
        });
        expect(parseCloudPointFrame).toHaveBeenCalledWith(buffer, {
            channelId: 1,
            timestampNs: '100'
        });
        expect(result).toBe(parsed);
    });

    it('throws without parsing when the response is not ok or has no data', async () => {
        vi.mocked(getPointCloud).mockResolvedValue({
            data: undefined,
            response: { ok: false, status: 404 } as Response
        } as Awaited<ReturnType<typeof getPointCloud>>);
        await expect(fetchCloudPointFrame(defaultArgs)).rejects.toThrow(
            'Could not load point cloud (404).'
        );

        vi.mocked(getPointCloud).mockResolvedValue({
            data: undefined,
            response: { ok: true, status: 200 } as Response
        } as Awaited<ReturnType<typeof getPointCloud>>);
        await expect(fetchCloudPointFrame(defaultArgs)).rejects.toThrow(
            'Could not load point cloud (200).'
        );

        vi.mocked(getPointCloud).mockResolvedValue({
            data: new ArrayBuffer(0),
            response: { ok: true, status: 200 } as Response
        } as Awaited<ReturnType<typeof getPointCloud>>);
        await expect(fetchCloudPointFrame(defaultArgs)).rejects.toThrow(
            'Could not load point cloud (200).'
        );

        expect(parseCloudPointFrame).not.toHaveBeenCalled();
    });
});
