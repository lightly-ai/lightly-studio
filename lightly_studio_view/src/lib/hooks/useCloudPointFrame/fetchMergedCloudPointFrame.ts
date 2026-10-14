import { fetchCloudPointFrame } from './fetchCloudPointFrame';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface FetchMergedCloudPointFrameParams extends CloudPointFrameParams {
    /** Abort signal shared by all channel requests. */
    signal?: AbortSignal;
}

/** Fetches every channel concurrently and merges them into one frame. */
export async function fetchMergedCloudPointFrame({
    datasetId,
    recordingId,
    channels,
    displayFrameId,
    signal
}: FetchMergedCloudPointFrameParams): Promise<CloudPointFrame> {
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
            fetchCloudPointFrame({ channel, datasetId, recordingId, displayFrameId, signal })
        )
    ]);
    return mergeCloudPointFrames(frames);
}
