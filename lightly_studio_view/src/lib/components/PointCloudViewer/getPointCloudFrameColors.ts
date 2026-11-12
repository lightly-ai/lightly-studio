import { Quaternion, Vector3 } from 'three';
import { getPointCloudColors } from './getPointCloudColors';
import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';

export interface CuboidGeometry {
    center: readonly [number, number, number];
    size: readonly [number, number, number];
    rotation: readonly [number, number, number, number];
    /** Keeps the points outside at full color. By default they are dimmed. */
    keepOutside?: boolean;
}

interface HighlightCacheEntry {
    baseColors: Float32Array;
    cuboid: CuboidGeometry;
    highlightedColors: Float32Array;
}

const intensityRanges = new WeakMap<PointBatch, [number, number]>();
const highlightColors = new WeakMap<PointBatch, HighlightCacheEntry>();

/** Preserves window-wide color normalization while reusing each sensor batch's colors. */
export function getPointCloudFrameColors(
    batch: PointBatch,
    mode: ColorMode,
    intensityRange?: [number, number],
    cameraColors?: Float32Array,
    highlightCuboid?: CuboidGeometry
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
        getHighlightedColors(segment, frameColors[index], highlightCuboid)
    );
}

function getHighlightedColors(
    segment: PointBatch,
    baseColors: Float32Array,
    cuboid: CuboidGeometry
): Float32Array {
    const cached = highlightColors.get(segment);
    if (cached && cached.baseColors === baseColors && sameCuboid(cached.cuboid, cuboid)) {
        return cached.highlightedColors;
    }
    const highlightedColors = blendCuboidColors(segment, baseColors, cuboid);
    highlightColors.set(segment, { baseColors, cuboid, highlightedColors });
    return highlightedColors;
}

function blendCuboidColors(
    segment: PointBatch,
    colors: Float32Array,
    cuboid: CuboidGeometry
): Float32Array {
    const highlighted = new Float32Array(colors.subarray(0, segment.count * 3));
    const inverseRotation = new Quaternion(...cuboid.rotation).invert();
    const localPoint = new Vector3();
    const halfSize = cuboid.size.map((size) => size / 2);
    const center = cuboid.center;
    const highlightColor = [1, 0.78, 0.08];

    for (let point = 0; point < segment.count; point++) {
        const offset = point * 3;
        const isInside = isPointInsideCuboid(
            segment.positions,
            offset,
            localPoint,
            center,
            halfSize,
            inverseRotation
        );
        if (isInside || !cuboid.keepOutside) {
            blendPointColor(highlighted, offset, isInside, highlightColor);
        }
    }
    return highlighted;
}

function isPointInsideCuboid(
    positions: Float32Array,
    offset: number,
    localPoint: Vector3,
    center: CuboidGeometry['center'],
    halfSize: number[],
    inverseRotation: Quaternion
): boolean {
    localPoint
        .set(
            positions[offset] - center[0],
            positions[offset + 1] - center[1],
            positions[offset + 2] - center[2]
        )
        .applyQuaternion(inverseRotation);
    return (
        Math.abs(localPoint.x) <= halfSize[0] &&
        Math.abs(localPoint.y) <= halfSize[1] &&
        Math.abs(localPoint.z) <= halfSize[2]
    );
}

function blendPointColor(
    colors: Float32Array,
    offset: number,
    inside: boolean,
    highlight: number[]
): void {
    const baseWeight = inside ? 0.15 : 0.12;
    const highlightWeight = inside ? 0.85 : 0;
    for (let channel = 0; channel < 3; channel++) {
        colors[offset + channel] =
            colors[offset + channel] * baseWeight + highlight[channel] * highlightWeight;
    }
}

function sameCuboid(a: CuboidGeometry, b: CuboidGeometry): boolean {
    return (
        a.center.every((value, index) => value === b.center[index]) &&
        a.size.every((value, index) => value === b.size[index]) &&
        a.rotation.every((value, index) => value === b.rotation[index]) &&
        a.keepOutside === b.keepOutside
    );
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
