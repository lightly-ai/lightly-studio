import { Box3, BufferAttribute, Vector3 } from 'three';
import { turboInto } from './colormap';

/** Determines how points are colored. */
export type ColorMode = 'none' | 'intensity' | 'height' | 'rgb';

/** Neutral gray used as a fallback color for points without explicit data. */
const NEUTRAL_GRAY = 0.5;

/** Camera position and orbit target computed from point cloud bounds. */
interface CameraPlacement {
    position: [number, number, number];
    target: [number, number, number];
}

/** Inputs for {@link buildColorBuffer}. */
interface BuildColorBufferParams {
    /** Flat positions [x0,y0,z0, x1,y1,z1, ...]. */
    positions: Float32Array;
    /** Per-point intensity values. */
    intensities: Float32Array;
    /** Number of active points. */
    count: number;
    /** "none", "intensity", "height", or "rgb". */
    colorMode: ColorMode;
    /** Pre-allocated output buffer (must be >= count * 3). */
    colors: Float32Array;
    /** Optional [min, max] override for intensity normalization. */
    intensityRange?: [number, number];
    /** Per-point linear RGB values used when colorMode is "rgb". */
    pointColors?: Float32Array;
}

/**
 * Build a color buffer from position and intensity data.
 *
 * @param params - See {@link BuildColorBufferParams}.
 */
export function buildColorBuffer(params: BuildColorBufferParams): void {
    const { colorMode, colors, count, pointColors } = params;

    if (colorMode === 'rgb' && pointColors) {
        colors.fill(NEUTRAL_GRAY, 0, count * 3);
        colors.set(pointColors.subarray(0, count * 3), 0);
        return;
    }

    if (colorMode === 'none' || colorMode === 'rgb') {
        colors.fill(NEUTRAL_GRAY, 0, count * 3);
        return;
    }
    fillGradient(params, colorMode === 'intensity');
}

/** Color the buffer with a turbo gradient over intensity or height values. */
function fillGradient(params: BuildColorBufferParams, useIntensity: boolean): void {
    const { positions, intensities, count, colors, intensityRange } = params;
    const valueAt = (i: number): number => (useIntensity ? intensities[i] : positions[i * 3 + 2]);
    const [minVal, maxVal] =
        useIntensity && intensityRange ? intensityRange : computeRange(valueAt, count);
    const range = maxVal - minVal;
    const invRange = range === 0 ? 0 : 1 / range;

    for (let i = 0; i < count; i++) {
        let t = (valueAt(i) - minVal) * invRange;
        if (t < 0) t = 0;
        else if (t > 1) t = 1;
        turboInto(useIntensity ? Math.sqrt(t) : t, colors, i * 3);
    }
}

/** Return the [min, max] of valueAt over the first count points. */
function computeRange(valueAt: (i: number) => number, count: number): [number, number] {
    let minVal = Infinity;
    let maxVal = -Infinity;
    for (let i = 0; i < count; i++) {
        const v = valueAt(i);
        if (v < minVal) minVal = v;
        if (v > maxVal) maxVal = v;
    }
    return [minVal, maxVal];
}

/**
 * Compute a Box3 from the first `count` points in a position buffer.
 */
export function computeActiveBounds(positions: Float32Array, count: number): Box3 {
    const attr = new BufferAttribute(positions.subarray(0, count * 3), 3);
    return new Box3().setFromBufferAttribute(attr);
}

/**
 * Compute camera placement from a precomputed bounding box.
 */
export function computeCameraPlacement(bounds: Box3): CameraPlacement {
    if (bounds.isEmpty()) {
        return { position: [0, 10, 20], target: [0, 0, 0] };
    }

    const center = bounds.getCenter(new Vector3());
    const size = bounds.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 1);
    const distance = maxDim * 1.5;

    return {
        position: [center.x + distance * 0.5, center.y + distance * 0.5, center.z + distance],
        target: [center.x, center.y, center.z]
    };
}
