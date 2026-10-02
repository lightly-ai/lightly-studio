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

/** Points drawn in a single color over the color mode, e.g. the points inside a selected box. */
export interface PointHighlight {
    /** One entry per point; a non-zero entry marks the point as highlighted. */
    mask: Uint8Array;
    /** Linear RGB color of the highlighted points, each channel in [0, 1]. */
    color: [number, number, number];
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
    /** Optional points to draw in a single color over the color mode. */
    highlight?: PointHighlight;
}

/**
 * Build a color buffer from position and intensity data.
 *
 * @param params - See {@link BuildColorBufferParams}.
 */
export function buildColorBuffer(params: BuildColorBufferParams): void {
    fillBaseColors(params);
    if (params.highlight) applyHighlight(params.colors, params.count, params.highlight);
}

/** Color the buffer by the color mode alone. */
function fillBaseColors(params: BuildColorBufferParams): void {
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

/** Overwrite the colors of the highlighted points among the first count points. */
function applyHighlight(colors: Float32Array, count: number, highlight: PointHighlight): void {
    const [r, g, b] = highlight.color;
    const end = Math.min(count, highlight.mask.length);
    let painted = 0;
    for (let i = 0; i < end; i++) {
        if (!highlight.mask[i]) continue;
        colors[i * 3] = r;
        colors[i * 3 + 1] = g;
        colors[i * 3 + 2] = b;
        painted++;
    }
    // DEBUG(cuboid-highlight): remove once the highlight is verified.
    console.debug('[cuboid-highlight] painted', {
        painted,
        count,
        maskLength: highlight.mask.length
    });
}

/**
 * Copy the positions of the highlighted points into a packed buffer.
 *
 * @param positions - Flat positions [x0,y0,z0, x1,y1,z1, ...].
 * @param count - Number of active points in `positions`.
 * @param mask - One entry per point; a non-zero entry marks the point as highlighted.
 * @returns Flat positions of the highlighted points only.
 */
export function extractHighlightedPositions(
    positions: Float32Array,
    count: number,
    mask: Uint8Array
): Float32Array {
    const end = Math.min(count, mask.length);
    let highlighted = 0;
    for (let i = 0; i < end; i++) if (mask[i]) highlighted++;
    const result = new Float32Array(highlighted * 3);
    let offset = 0;
    for (let i = 0; i < end; i++) {
        if (!mask[i]) continue;
        result.set(positions.subarray(i * 3, i * 3 + 3), offset);
        offset += 3;
    }
    return result;
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
