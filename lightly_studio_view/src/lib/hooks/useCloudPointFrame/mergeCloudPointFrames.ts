import { mergeBounds } from './mergeBounds';
import type { CloudPointFrame } from './types';

export function mergeCloudPointFrames(frames: CloudPointFrame[]): CloudPointFrame {
    const pointCount = frames.reduce((total, frame) => total + frame.batch.count, 0);
    const positions = new Float32Array(pointCount * 3);
    const intensities = new Float32Array(pointCount);
    const hasColors = frames.every((frame) => frame.batch.colors);
    const colors = hasColors ? new Float32Array(pointCount * 3) : undefined;
    let pointOffset = 0;
    for (const frame of frames) {
        positions.set(frame.batch.positions, pointOffset * 3);
        intensities.set(frame.batch.intensities, pointOffset);
        if (colors && frame.batch.colors) colors.set(frame.batch.colors, pointOffset * 3);
        pointOffset += frame.batch.count;
    }
    const bounds = mergeBounds(frames.map((frame) => frame.bounds));
    const first = frames[0];
    return {
        batch: { positions, intensities, ...(colors ? { colors } : {}), count: pointCount },
        channelId: first.channelId,
        timestampNs: first.timestampNs,
        frameId: frames.map((frame) => frame.frameId).join(','),
        sourcePointCount: frames.reduce((total, frame) => total + frame.sourcePointCount, 0),
        bounds,
        channels: frames.flatMap((frame) => frame.channels)
    };
}
