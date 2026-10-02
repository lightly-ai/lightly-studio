import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useCloudPointFrame } from './useCloudPointFrame.svelte';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame } from './types';

vi.mock('./fetchCloudPointFrame', () => ({ fetchCloudPointFrame: vi.fn() }));
vi.mock('./mergeCloudPointFrames', () => ({ mergeCloudPointFrames: vi.fn() }));

interface QueryOptions {
    queryKey: unknown[];
    enabled: boolean;
    placeholderData: (previous: CloudPointFrame | undefined) => CloudPointFrame | undefined;
    queryFn: (context: { signal?: AbortSignal }) => Promise<CloudPointFrame>;
}

const defaultParams = () => ({
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channels: [
        { channelId: 1, timestampNs: '100' },
        { channelId: 2, timestampNs: '200' }
    ]
});

function getQueryOptions(
    getParams: () => ReturnType<typeof defaultParams> & { targetFrameId?: string }
): QueryOptions {
    const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
    useCloudPointFrame(getParams);
    return createQuerySpy.mock.lastCall?.[0]() as unknown as QueryOptions;
}

describe('useCloudPointFrame', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(
            {} as CreateQueryResult<CloudPointFrame, Error>
        );
    });

    it('builds a query key from the dataset, recording, and channels', () => {
        const options = getQueryOptions(defaultParams);

        expect(options.queryKey).toEqual([
            'cloud-point-frame',
            'dataset-1',
            'recording-1',
            defaultParams().channels,
            ''
        ]);
    });

    it('is enabled only when dataset, recording, and channels are all present', () => {
        expect(getQueryOptions(defaultParams).enabled).toBe(true);
        expect(getQueryOptions(() => ({ ...defaultParams(), channels: [] })).enabled).toBe(false);
        expect(getQueryOptions(() => ({ ...defaultParams(), datasetId: '' })).enabled).toBe(false);
        expect(getQueryOptions(() => ({ ...defaultParams(), recordingId: '' })).enabled).toBe(
            false
        );
    });

    it('fetches every channel and merges the resulting frames', async () => {
        const merged = { frameId: 'merged' } as unknown as CloudPointFrame;
        vi.mocked(fetchCloudPointFrame).mockImplementation(
            async ({ channel }) => ({ frameId: `frame-${channel.channelId}` }) as CloudPointFrame
        );
        vi.mocked(mergeCloudPointFrames).mockReturnValue(merged);

        const signal = new AbortController().signal;
        const result = await getQueryOptions(defaultParams).queryFn({ signal });

        expect(fetchCloudPointFrame).toHaveBeenCalledTimes(2);
        expect(fetchCloudPointFrame).toHaveBeenNthCalledWith(1, {
            datasetId: 'dataset-1',
            recordingId: 'recording-1',
            channel: { channelId: 1, timestampNs: '100' },
            targetFrameId: undefined,
            signal
        });
        expect(mergeCloudPointFrames).toHaveBeenCalledWith([
            { frameId: 'frame-1' },
            { frameId: 'frame-2' }
        ]);
        expect(result).toBe(merged);
    });

    it('fetches every channel in the target frame', async () => {
        vi.mocked(fetchCloudPointFrame).mockResolvedValue({ frameId: 'map' } as CloudPointFrame);

        await getQueryOptions(() => ({ ...defaultParams(), targetFrameId: 'map' })).queryFn({});

        expect(fetchCloudPointFrame).toHaveBeenCalledTimes(2);
        expect(
            vi.mocked(fetchCloudPointFrame).mock.calls.map(([args]) => args.targetFrameId)
        ).toEqual(['map', 'map']);
    });

    it('falls back to the sensor frames when the target frame fails', async () => {
        const merged = { frameId: 'lidar-1,lidar-2' } as unknown as CloudPointFrame;
        vi.mocked(fetchCloudPointFrame).mockImplementation(async ({ channel, targetFrameId }) => {
            if (targetFrameId) throw new Error('Could not load point cloud (400).');
            return { frameId: `lidar-${channel.channelId}` } as CloudPointFrame;
        });
        vi.mocked(mergeCloudPointFrames).mockReturnValue(merged);

        const result = await getQueryOptions(() => ({
            ...defaultParams(),
            targetFrameId: 'map'
        })).queryFn({});

        expect(result).toBe(merged);
        expect(mergeCloudPointFrames).toHaveBeenCalledWith([
            { frameId: 'lidar-1' },
            { frameId: 'lidar-2' }
        ]);
    });

    it('does not fall back without a target frame', async () => {
        vi.mocked(fetchCloudPointFrame).mockRejectedValue(new Error('Could not load (500).'));

        await expect(getQueryOptions(defaultParams).queryFn({})).rejects.toThrow('(500)');
        expect(fetchCloudPointFrame).toHaveBeenCalledTimes(2);
    });

    it('keeps the previous point cloud while the next tick loads', () => {
        const previous = { frameId: 'previous' } as unknown as CloudPointFrame;
        const options = getQueryOptions(defaultParams);

        expect(options.placeholderData(previous)).toBe(previous);
        expect(options.placeholderData(undefined)).toBeUndefined();
    });
});
