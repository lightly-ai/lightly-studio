import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface UseCloudPointFrameReturn {
    query: CreateQueryResult<CloudPointFrame, Error>;
}

/**
 * Fetches and merges cloud point frames across the requested channels.
 *
 * Each channel is fetched in parallel and the results are combined into a single
 * frame. If the frame cannot be loaded in `targetFrameId`, it is loaded in the sensor
 * frames instead, which the `frameId` of each merged channel shows. Accepts a getter (thunk) so the query stays reactive to parameter changes.
 *
 * @param getParams - Reactive getter for the dataset, recording, and channels to load.
 * @returns The TanStack Query result exposing the merged cloud point frame.
 */
export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): UseCloudPointFrameReturn => {
    const query = createQuery(() => {
        const { datasetId, recordingId, channels, targetFrameId } = getParams();
        return {
            queryKey: ['cloud-point-frame', datasetId, recordingId, channels, targetFrameId ?? ''],
            // Skip fetching until a dataset, recording, and at least one channel are known.
            enabled: Boolean(datasetId && recordingId && channels.length),
            // Preserve the mounted scene and its camera while the next tick is loading.
            placeholderData: (previous: CloudPointFrame | undefined) => previous,
            queryFn: async ({ signal }): Promise<CloudPointFrame> => {
                try {
                    return await fetchMergedFrame({
                        datasetId,
                        recordingId,
                        channels,
                        targetFrameId,
                        signal
                    });
                } catch (error) {
                    // A tick without a transform to the target frame, e.g. a gap in `/tf`,
                    // still renders. Every channel falls back so the frames never mix.
                    if (!targetFrameId || signal?.aborted) throw error;
                    return fetchMergedFrame({ datasetId, recordingId, channels, signal });
                }
            }
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
    targetFrameId,
    signal
}: FetchMergedFrameParams): Promise<CloudPointFrame> {
    const [firstChannel, ...otherChannels] = channels;
    if (!firstChannel) throw new Error('No point cloud channels to load.');
    const frames = await Promise.all([
        fetchCloudPointFrame({
            datasetId,
            recordingId,
            channel: firstChannel,
            targetFrameId,
            signal
        }),
        ...otherChannels.map((channel) =>
            fetchCloudPointFrame({ datasetId, recordingId, channel, targetFrameId, signal })
        )
    ]);
    return mergeCloudPointFrames(frames);
}
