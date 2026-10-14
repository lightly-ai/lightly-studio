import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { getCloudPointFrameOptions } from './getCloudPointFrameOptions';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface UseCloudPointFrameReturn {
    /** Query result for the merged point-cloud frame. */
    query: CreateQueryResult<CloudPointFrame, Error>;
}

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
        const { datasetId, recordingId, channels, displayFrameId } = getParams();
        return {
            ...getCloudPointFrameOptions({ datasetId, recordingId, channels, displayFrameId }),
            // Skip fetching until a dataset, recording, and at least one channel are known.
            enabled: Boolean(datasetId && recordingId && channels.length),
            // Preserve the mounted scene and its camera while the next tick is loading.
            placeholderData: (previous: CloudPointFrame | undefined) => previous
        };
    });
    return { query };
};
