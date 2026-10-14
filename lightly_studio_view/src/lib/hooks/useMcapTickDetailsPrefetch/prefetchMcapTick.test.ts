import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/svelte-query';
import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getCloudPointFrameOptions } from '$lib/hooks/useCloudPointFrame/getCloudPointFrameOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { prefetchCameraFrame } from './prefetchCameraFrame';
import { prefetchMcapTick } from './prefetchMcapTick';

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    getSummaryOptions: vi.fn(() => ({ queryKey: ['summary'] }))
}));
vi.mock('$lib/hooks/useCloudPointFrame/getCloudPointFrameOptions', () => ({
    getCloudPointFrameOptions: vi.fn(() => ({ queryKey: ['cloud-point-frame'] }))
}));
vi.mock('$lib/hooks/useTickDetails/getTickDetailsOptions', () => ({
    getTickDetailsOptions: vi.fn(() => ({ queryKey: ['tick-details'] }))
}));
vi.mock('./prefetchCameraFrame', () => ({
    prefetchCameraFrame: vi.fn().mockResolvedValue({ data: new ArrayBuffer(0) })
}));

describe('prefetchMcapTick', () => {
    beforeEach(() => vi.clearAllMocks());

    it('caches tick details and point-cloud data and warms camera image cache', async () => {
        const client = {
            ensureQueryData: vi
                .fn()
                .mockResolvedValueOnce({
                    lidar_channels: [{ channel_id: 3, group_component_name: 'lidar' }],
                    camera_channels: [{ channel_id: 7, group_component_name: 'front' }]
                })
                .mockResolvedValueOnce({
                    recording_id: 'recording-1',
                    lidar_channels: {
                        lidar: { channel_id: 3, log_time_ns: '1000' }
                    },
                    camera_channels: {
                        front: {
                            keyframe_log_time_ns: '2000',
                            log_time_ns: '2010'
                        }
                    }
                })
        } as unknown as QueryClient;

        await prefetchMcapTick(client, {
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 4,
            displayFrameId: 'base_link'
        });

        expect(client.ensureQueryData).toHaveBeenCalledTimes(3);
        expect(getSummaryOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' }
        });
        expect(getTickDetailsOptions).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 4,
            displayFrameId: 'base_link'
        });
        expect(client.ensureQueryData).toHaveBeenCalledWith({ queryKey: ['cloud-point-frame'] });
        expect(getCloudPointFrameOptions).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channels: [{ channelId: 3, timestampNs: '1000' }],
            displayFrameId: 'base_link'
        });
        expect(prefetchCameraFrame).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel: { channel_id: 7, group_component_name: 'front' },
            frame: { keyframe_log_time_ns: '2000', log_time_ns: '2010' }
        });
    });

    it('skips frame prefetches when the tick has no configured channels', async () => {
        const client = {
            ensureQueryData: vi
                .fn()
                .mockResolvedValueOnce({ lidar_channels: [], camera_channels: [] })
                .mockResolvedValueOnce({
                    recording_id: 'recording-1',
                    lidar_channels: {},
                    camera_channels: {}
                })
        } as unknown as QueryClient;

        await prefetchMcapTick(client, {
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 4
        });

        expect(client.ensureQueryData).toHaveBeenCalledTimes(2);
        expect(prefetchCameraFrame).not.toHaveBeenCalled();
    });

    it('propagates point-cloud errors so a failed tick cannot be marked buffered', async () => {
        const error = new Error('Point cloud unavailable');
        const client = {
            ensureQueryData: vi
                .fn()
                .mockResolvedValueOnce({
                    lidar_channels: [{ group_component_name: 'lidar' }],
                    camera_channels: []
                })
                .mockResolvedValueOnce({
                    recording_id: 'recording-1',
                    lidar_channels: { lidar: { channel_id: 3, log_time_ns: '1000' } },
                    camera_channels: {}
                })
                .mockRejectedValueOnce(error)
        } as unknown as QueryClient;

        await expect(
            prefetchMcapTick(client, {
                datasetId: 'dataset-1',
                sequenceId: 'sequence-1',
                seqNumber: 4
            })
        ).rejects.toBe(error);
    });
});
