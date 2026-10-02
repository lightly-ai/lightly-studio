import type { PointBatch } from '$lib/components/PointCloudViewer';
import { mergeBounds } from './mergeBounds';
import type { CloudPointFrame } from './types';

/** A non-empty list of frames, so the first frame is always available. */
type NonEmptyFrames = [CloudPointFrame, ...CloudPointFrame[]];

export function mergeCloudPointFrames(frames: NonEmptyFrames): CloudPointFrame {
    const batch = mergeBatches(frames.map((frame) => frame.batch));
    const bounds = mergeFrameBounds(frames);
    const first = frames[0];
    return {
        batch,
        channelId: first.channelId,
        timestampNs: first.timestampNs,
        frameId: frames.map((frame) => frame.frameId).join(','),
        sourcePointCount: frames.reduce((total, frame) => total + frame.sourcePointCount, 0),
        bounds,
        channels: frames.flatMap((frame) => frame.channels)
    };
}

/**
 * Merges the bounds of the frames that carry points. Returns `null` when any
 * such frame lacks bounds, so the result never claims a box that excludes some
 * of the merged points.
 */
function mergeFrameBounds(frames: NonEmptyFrames): CloudPointFrame['bounds'] {
    const contributing = frames.filter((frame) => frame.batch.count > 0);
    if (contributing.some((frame) => frame.bounds === null)) return null;
    return mergeBounds(contributing.map((frame) => frame.bounds));
}

/** Concatenates the active points of several batches into one packed batch. */
export function mergeBatches(batches: PointBatch[]): PointBatch {
    const count = batches.reduce((total, batch) => total + batch.count, 0);
    const positions = new Float32Array(count * 3);
    const intensities = new Float32Array(count);
    const hasColors = batches.every((batch) => batch.count === 0 || batch.colors);
    const colors = hasColors ? new Float32Array(count * 3) : undefined;
    let offset = 0;
    for (const batch of batches) {
        positions.set(batch.positions.subarray(0, batch.count * 3), offset * 3);
        intensities.set(batch.intensities.subarray(0, batch.count), offset);
        if (colors && batch.colors)
            colors.set(batch.colors.subarray(0, batch.count * 3), offset * 3);
        offset += batch.count;
    }
    return { positions, intensities, ...(colors ? { colors } : {}), count };
}
