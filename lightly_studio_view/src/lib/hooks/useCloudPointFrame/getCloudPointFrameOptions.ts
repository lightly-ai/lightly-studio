import { fetchMergedCloudPointFrame } from './fetchMergedCloudPointFrame';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

/** Builds the cacheable query used by both the visible frame and range prefetching. */
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
            return await fetchMergedCloudPointFrame({ ...params, signal });
        } catch (error) {
            // A tick without a transform to the target, e.g. a gap in `/tf`, still renders.
            if (!params.displayFrameId || signal?.aborted) throw error;
            return fetchMergedCloudPointFrame({ ...params, displayFrameId: undefined, signal });
        }
    }
});
