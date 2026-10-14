import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useCloudPointFrame } from './useCloudPointFrame.svelte';
import { getCloudPointFrameOptions } from './getCloudPointFrameOptions';
import type { CloudPointFrame } from './types';

vi.mock('./getCloudPointFrameOptions', () => ({
    getCloudPointFrameOptions: vi.fn(() => ({
        queryKey: ['cloud-point-frame'],
        queryFn: vi.fn()
    }))
}));

const defaultParams = () => ({
    datasetId: 'dataset-1',
    recordingId: 'recording-1',
    channels: [{ channelId: 1, timestampNs: '100' }]
});

function getQueryOptions(
    getParams: () => ReturnType<typeof defaultParams> & { displayFrameId?: string }
) {
    const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
    useCloudPointFrame(getParams);
    return createQuerySpy.mock.lastCall?.[0] as () => {
        queryKey: unknown[];
        queryFn: unknown;
        enabled: boolean;
        placeholderData: (previous: CloudPointFrame | undefined) => CloudPointFrame | undefined;
    };
}

describe('useCloudPointFrame', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(
            {} as CreateQueryResult<CloudPointFrame, Error>
        );
    });

    it('builds the shared cloud-point query options from reactive parameters', () => {
        const getParams = () => ({ ...defaultParams(), displayFrameId: 'base_link' });
        const options = getQueryOptions(getParams)();

        expect(getCloudPointFrameOptions).toHaveBeenCalledWith(getParams());
        expect(options.queryKey).toEqual(['cloud-point-frame']);
    });

    it('enables fetching only when dataset, recording, and channels are present', () => {
        expect(getQueryOptions(defaultParams)().enabled).toBe(true);
        expect(getQueryOptions(() => ({ ...defaultParams(), channels: [] }))().enabled).toBe(false);
        expect(getQueryOptions(() => ({ ...defaultParams(), datasetId: '' }))().enabled).toBe(
            false
        );
        expect(getQueryOptions(() => ({ ...defaultParams(), recordingId: '' }))().enabled).toBe(
            false
        );
    });

    it('keeps the previous point cloud while the next tick loads', () => {
        const previous = { frameId: 'previous' } as unknown as CloudPointFrame;
        const options = getQueryOptions(defaultParams)();

        expect(options.placeholderData(previous)).toBe(previous);
        expect(options.placeholderData(undefined)).toBeUndefined();
    });
});
