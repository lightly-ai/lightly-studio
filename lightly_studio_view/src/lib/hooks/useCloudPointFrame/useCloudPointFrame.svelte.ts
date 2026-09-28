import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

/**
 * Fetches and merges cloud point frames across the requested channels.
 *
 * Each channel is fetched in parallel and the results are combined into a single
 * frame. Accepts a getter (thunk) so the query stays reactive to parameter changes.
 *
 * @param getParams - Reactive getter for the dataset, recording, and channels to load.
 * @returns The TanStack Query result exposing the merged cloud point frame.
 */
export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): { query: CreateQueryResult<CloudPointFrame, Error> } => {
    const query = createQuery(() => {
        const { datasetId, recordingId, channels } = getParams();
        return {
            queryKey: ['cloud-point-frame', datasetId, recordingId, channels],
            // Skip fetching until a dataset, recording, and at least one channel are known.
            enabled: Boolean(datasetId && recordingId && channels.length),
            queryFn: async ({ signal }): Promise<CloudPointFrame> => {
                // Fetch every channel concurrently; `signal` cancels in-flight requests.
                const frames = await Promise.all(
                    channels.map((channel) =>
                        fetchCloudPointFrame({ datasetId, recordingId, channel, signal })
                    )
                );
                // Combine the per-channel frames into one merged frame.
                return mergeCloudPointFrames(frames);
            }
        };
    });
    return { query };
};
