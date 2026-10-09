import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface UseCloudPointFrameReturn {
    query: CreateQueryResult<CloudPointFrame, Error>;
}

/** Builds the cacheable query used for a merged point-cloud frame. */
export const getCloudPointFrameOptions = (params: CloudPointFrameParams) => ({
    queryKey: [
        'cloud-point-frame',
        params.datasetId,
        params.recordingId,
        params.channels,
        params.displayFrameId ?? ''
    ],
    queryFn: async ({ signal }: { signal?: AbortSignal }): Promise<CloudPointFrame> => {
        try {
            return await fetchMergedFrame({ ...params, signal });
        } catch (error) {
            if (!params.displayFrameId || signal?.aborted) throw error;
            return fetchMergedFrame({ ...params, displayFrameId: undefined, signal });
        }
    }
});

/**
 * Fetches and merges cloud point frames across the requested channels.
 *
 * Each channel is fetched in parallel and the results are combined into a single
 * frame. If the frame cannot be loaded in `displayFrameId`, it is loaded in the sensor
 * frames instead, which the `frameId` of each merged channel shows. Accepts a getter (thunk) so the query stays reactive to parameter changes.
 *
 * @param getParams - Reactive getter for the dataset, recording, and channels to load.
 * @returns The TanStack Query result exposing the merged cloud point frame.
 */
export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): UseCloudPointFrameReturn => {
    const query = createQuery(() => {
        const params = getParams();
        return {
            ...getCloudPointFrameOptions(params),
            // Skip fetching until a dataset, recording, and at least one channel are known.
            enabled: Boolean(params.datasetId && params.recordingId && params.channels.length),
            // Preserve the mounted scene and its camera while the next tick is loading.
            placeholderData: (previous: CloudPointFrame | undefined) => previous
        };
    });
    return { query };
};

interface FetchMergedFrameParams extends CloudPointFrameParams {
    signal?: AbortSignal;
}

/** Fetches every channel concurrently and merges them; `signal` cancels in-flight requests. */
async function fetchMergedFrame({
    datasetId,
    recordingId,
    channels,
    displayFrameId,
    signal
}: FetchMergedFrameParams): Promise<CloudPointFrame> {
    const [firstChannel, ...otherChannels] = channels;
    if (!firstChannel) throw new Error('No point cloud channels to load.');
    const frames = await Promise.all([
        fetchCloudPointFrame({
            datasetId,
            recordingId,
            channel: firstChannel,
            displayFrameId,
            signal
        }),
        ...otherChannels.map((channel) =>
            fetchCloudPointFrame({ datasetId, recordingId, channel, displayFrameId, signal })
        )
    ]);
    return mergeCloudPointFrames(frames);
}
