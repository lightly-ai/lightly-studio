import { mergePointBatches } from './mergePointBatches';
import { createSegmentedPointBatch } from './createSegmentedPointBatch';
import { mergeBounds } from './mergeBounds';
import type { CloudPointFrame } from './types';

/** A non-empty list of frames, so the first frame is always available. */
type NonEmptyFrames = [CloudPointFrame, ...CloudPointFrame[]];

interface MergeOptions {
    segmented?: boolean;
}

export function mergeCloudPointFrames(
    frames: NonEmptyFrames,
    { segmented = false }: MergeOptions = {}
): CloudPointFrame {
    const batches = frames.map((frame) => frame.batch);
    const batch = segmented ? createSegmentedPointBatch(batches) : mergePointBatches(batches);
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
