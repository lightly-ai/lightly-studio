import { Box3, BufferAttribute, Vector3 } from 'three';
import { turboInto } from './colormap';

/** Determines how points are colored. */
export type ColorMode = 'none' | 'intensity' | 'height';

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
    /** How points are colored. */
    colorMode: ColorMode;
    /** Pre-allocated output buffer (must be >= count * 3). */
    colors: Float32Array;
    /** Optional [min, max] override for intensity normalization. */
    intensityRange?: [number, number];
}

/**
 * Build a color buffer from position and intensity data.
 */
export function buildColorBuffer(params: BuildColorBufferParams): void {
    const { colorMode, colors, count } = params;

    if (colorMode === 'none') {
        fillNeutralColors(colors, count);
        return;
    }
    fillGradientColors(params);
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

/** Fill the color buffer with neutral gray for the first `count` points. */
function fillNeutralColors(colors: Float32Array, count: number): void {
    for (let i = 0; i < count; i++) {
        colors[i * 3] = NEUTRAL_GRAY;
        colors[i * 3 + 1] = NEUTRAL_GRAY;
        colors[i * 3 + 2] = NEUTRAL_GRAY;
    }
}

/** Color the points along the turbo gradient using intensity or height. */
function fillGradientColors(params: BuildColorBufferParams): void {
    const { positions, intensities, count, colorMode, colors, intensityRange } = params;
    const useIntensity = colorMode === 'intensity';

    const [minVal, maxVal] =
        useIntensity && intensityRange
            ? intensityRange
            : computeValueRange(positions, intensities, count, useIntensity);

    const range = maxVal - minVal;
    const invRange = range === 0 ? 0 : 1 / range;

    for (let i = 0; i < count; i++) {
        const raw = useIntensity ? intensities[i] : positions[i * 3 + 2];

        let t = (raw - minVal) * invRange;
        if (t < 0) t = 0;
        else if (t > 1) t = 1;
        if (useIntensity) t = Math.sqrt(t);

        turboInto(t, colors, i * 3);
    }
}

/** Find the [min, max] of the intensity or height values across active points. */
function computeValueRange(
    positions: Float32Array,
    intensities: Float32Array,
    count: number,
    useIntensity: boolean
): [number, number] {
    let minVal = Infinity;
    let maxVal = -Infinity;
    for (let i = 0; i < count; i++) {
        const v = useIntensity ? intensities[i] : positions[i * 3 + 2];
        if (v < minVal) minVal = v;
        if (v > maxVal) maxVal = v;
    }
    return [minVal, maxVal];
}
