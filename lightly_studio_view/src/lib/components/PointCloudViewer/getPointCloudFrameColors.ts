import { Quaternion, Vector3 } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { getPointCloudColors } from './getPointCloudColors';
import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';

const intensityRanges = new WeakMap<PointBatch, [number, number]>();

/** Preserves window-wide color normalization while reusing each sensor batch's colors. */
export function getPointCloudFrameColors(
    batch: PointBatch,
    mode: ColorMode,
    intensityRange?: [number, number],
    cameraColors?: Float32Array,
    highlightCuboid?: CuboidAnnotation
): Float32Array[] {
    const segments = batch.segments ?? [batch];
    let frameColors: Float32Array[];
    if (mode === 'camera-rgb') {
        // Camera RGB colors are computed over the whole accumulation window; split per segment.
        // Without colors yet (async), fall back to neutral so points stay visible.
        frameColors = !cameraColors
            ? segments.map((segment) => getPointCloudColors(segment, 'none'))
            : splitColors(cameraColors, segments);
    } else if (mode === 'intensity') {
        const range = intensityRange ?? getWindowIntensityRange(segments);
        frameColors = segments.map((segment) => getPointCloudColors(segment, mode, range));
    } else if (mode === 'none' || mode === 'rgb') {
        const hasColors = segments.every((segment) => !segment.count || segment.colors);
        const effectiveMode = mode === 'rgb' && !hasColors ? 'none' : mode;
        frameColors = segments.map((segment) => getPointCloudColors(segment, effectiveMode));
    } else {
        frameColors = splitColors(getPointCloudColors(batch, mode, intensityRange), segments);
    }
    if (!highlightCuboid) return frameColors;
    return segments.map((segment, index) =>
        highlightCuboidPoints(segment.positions, frameColors[index], segment.count, highlightCuboid)
    );
}

function highlightCuboidPoints(
    positions: Float32Array,
    colors: Float32Array,
    count: number,
    cuboid: CuboidAnnotation
): Float32Array {
    const highlighted = new Float32Array(colors.subarray(0, count * 3));
    const inverseRotation = new Quaternion(...cuboid.rotation).invert();
    const localPoint = new Vector3();
    const halfSize = cuboid.size.map((size) => size / 2);
    const center = cuboid.center;
    const highlightColor = [1, 0.78, 0.08];

    for (let point = 0; point < count; point++) {
        const offset = point * 3;
        localPoint
            .set(
                positions[offset] - center[0],
                positions[offset + 1] - center[1],
                positions[offset + 2] - center[2]
            )
            .applyQuaternion(inverseRotation);
        const isInside =
            Math.abs(localPoint.x) <= halfSize[0] &&
            Math.abs(localPoint.y) <= halfSize[1] &&
            Math.abs(localPoint.z) <= halfSize[2];
        const baseWeight = isInside ? 0.15 : 0.12;
        const highlightWeight = isInside ? 0.85 : 0;
        for (let channel = 0; channel < 3; channel++) {
            highlighted[offset + channel] =
                highlighted[offset + channel] * baseWeight +
                highlightColor[channel] * highlightWeight;
        }
    }
    return highlighted;
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
