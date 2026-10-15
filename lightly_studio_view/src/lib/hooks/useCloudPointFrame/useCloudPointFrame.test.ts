import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import type { TickData } from '$lib/hooks/useTickData/fetchTickData';
import { useCloudPointFrame } from './useCloudPointFrame.svelte';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

vi.mock('$lib/hooks/useTickData/getTickDataOptions', () => ({
    getTickDataOptions: vi.fn(() => ({ queryKey: ['tick-data'], queryFn: vi.fn() }))
}));

const defaultParams = (): CloudPointFrameParams => ({
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 4
});

function getQueryOptions(getParams: () => CloudPointFrameParams) {
    const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
    useCloudPointFrame(getParams);
    return createQuerySpy.mock.lastCall?.[0] as () => {
        queryKey: unknown[];
        enabled: boolean;
        select: (data: TickData) => CloudPointFrame;
        placeholderData: (previous: TickData | undefined) => TickData | undefined;
    };
}

function frame(channelId: number, count: number): CloudPointFrame {
    return {
        batch: {
            positions: new Float32Array(count * 3),
            intensities: new Float32Array(count),
            count
        },
        channelId,
        timestampNs: '100',
        frameId: `lidar-${channelId}`,
        sourcePointCount: count,
        bounds: null,
        channels: [{ channelId, timestampNs: '100', frameId: `lidar-${channelId}` }]
    };
}

describe('useCloudPointFrame', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(
            {} as CreateQueryResult<CloudPointFrame, Error>
        );
    });

    it('reads the shared tick-data query of the tick', () => {
        const options = getQueryOptions(() => ({
            ...defaultParams(),
            displayFrameId: 'base_link',
            selectedChannelIds: [1]
        }))();

        expect(getTickDataOptions).toHaveBeenCalledWith({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 4,
            displayFrameId: 'base_link'
        });
        expect(options.queryKey).toEqual(['tick-data']);
    });

    it('enables fetching only for a known tick with at least one selected lidar', () => {
        expect(getQueryOptions(defaultParams)().enabled).toBe(true);
        expect(
            getQueryOptions(() => ({ ...defaultParams(), selectedChannelIds: [] }))().enabled
        ).toBe(false);
        expect(getQueryOptions(() => ({ ...defaultParams(), datasetId: '' }))().enabled).toBe(
            false
        );
        expect(getQueryOptions(() => ({ ...defaultParams(), sequenceId: '' }))().enabled).toBe(
            false
        );
    });

    it('merges the point clouds of the selected lidar channels', () => {
        const data: TickData = { pointClouds: [frame(1, 2), frame(2, 3)], cameraFrames: {} };

        const all = getQueryOptions(defaultParams)().select(data);
        const selected = getQueryOptions(() => ({
            ...defaultParams(),
            selectedChannelIds: [2]
        }))().select(data);

        expect(all.batch.count).toBe(5);
        expect(all.channels.map((channel) => channel.channelId)).toEqual([1, 2]);
        expect(selected.batch.count).toBe(3);
        expect(selected.channels.map((channel) => channel.channelId)).toEqual([2]);
    });

    it('keeps the previous tick data while the next tick loads', () => {
        const previous: TickData = { pointClouds: [], cameraFrames: {} };
        const options = getQueryOptions(defaultParams)();

        expect(options.placeholderData(previous)).toBe(previous);
        expect(options.placeholderData(undefined)).toBeUndefined();
    });
});
