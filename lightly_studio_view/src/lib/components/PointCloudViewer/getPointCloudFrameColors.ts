import { getPointCloudColors } from './getPointCloudColors';
import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';

const intensityRanges = new WeakMap<PointBatch, [number, number]>();

/** Preserves window-wide color normalization while reusing each sensor batch's colors. */
export function getPointCloudFrameColors(
    batch: PointBatch,
    mode: ColorMode,
    intensityRange?: [number, number]
): Float32Array[] {
    const segments = batch.segments ?? [batch];
    if (mode === 'intensity') {
        const range = intensityRange ?? getWindowIntensityRange(segments);
        return segments.map((segment) => getPointCloudColors(segment, mode, range));
    }
    if (mode === 'none' || mode === 'rgb') {
        const hasColors = segments.every((segment) => !segment.count || segment.colors);
        const effectiveMode = mode === 'rgb' && !hasColors ? 'none' : mode;
        return segments.map((segment) => getPointCloudColors(segment, effectiveMode));
    }
    return splitColors(getPointCloudColors(batch, mode, intensityRange), segments);
}

function getWindowIntensityRange(segments: readonly PointBatch[]): [number, number] {
    let min = Infinity;
    let max = -Infinity;
    for (const segment of segments) {
        const range = getIntensityRange(segment);
        min = Math.min(min, range[0]);
        max = Math.max(max, range[1]);
    }
    return [min, max];
}

function getIntensityRange(batch: PointBatch): [number, number] {
    const previous = intensityRanges.get(batch);
    if (previous) return previous;
    let min = Infinity;
    let max = -Infinity;
    for (let index = 0; index < batch.count; index++) {
        const value = batch.intensities[index];
        min = Math.min(min, value);
        max = Math.max(max, value);
    }
    const range: [number, number] = [min, max];
    intensityRanges.set(batch, range);
    return range;
}

function splitColors(colors: Float32Array, segments: readonly PointBatch[]): Float32Array[] {
    let offset = 0;
    return segments.map((segment) => {
        const start = offset;
        offset += segment.count * 3;
        return colors.subarray(start, offset);
    });
}
