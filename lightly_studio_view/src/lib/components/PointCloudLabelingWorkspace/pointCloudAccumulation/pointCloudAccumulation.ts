import type { PointBatch } from '$lib/components/PointCloudViewer';
import { mergeBatches } from '$lib/hooks/useCloudPointFrame/mergeCloudPointFrames';
import type { CloudPointFrame } from '$lib/hooks/useCloudPointFrame/types';

/** Points collected across ticks while the scene accumulates point clouds. */
export interface PointCloudAccumulation {
    /** Identifies what was accumulated, e.g. the source, frame, and channels; a new key restarts. */
    readonly key: string;
    /** IDs of the point clouds already merged into `batch`, so none is added twice. */
    readonly loadedClouds: ReadonlySet<string>;
    /** Every point collected so far. */
    readonly batch: PointBatch;
}

/**
 * Adds the points of a frame to an accumulation.
 *
 * Starts over when there is no accumulation yet or its key differs, and returns the accumulation
 * unchanged when the frame is already part of it, e.g. when the user steps back to a tick.
 *
 * @param accumulation - The points collected so far, or `null` to start.
 * @param key - Identifies what is accumulated; a change discards the collected points.
 * @param frame - The loaded frame to add.
 * @returns The accumulation that includes the points of `frame`.
 */
export function accumulatePointCloud(
    accumulation: PointCloudAccumulation | null,
    key: string,
    frame: CloudPointFrame
): PointCloudAccumulation {
    const cloudId = frame.channels
        .map((channel) => `${channel.channelId}@${channel.timestampNs}`)
        .join(',');
    if (accumulation?.key !== key) {
        return { key, loadedClouds: new Set([cloudId]), batch: frame.batch };
    }
    if (accumulation.loadedClouds.has(cloudId)) return accumulation;
    return {
        key,
        loadedClouds: new Set([...accumulation.loadedClouds, cloudId]),
        batch: mergeBatches([accumulation.batch, frame.batch])
    };
}
