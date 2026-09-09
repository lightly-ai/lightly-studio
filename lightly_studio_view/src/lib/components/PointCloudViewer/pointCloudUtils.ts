import { Box3, BufferAttribute, Vector3 } from 'three';
import { turboInto } from './colormap';

/** Determines how points are colored. */
export type ColorMode = 'none' | 'intensity' | 'height';

/** Camera position and orbit target computed from point cloud bounds. */
interface CameraPlacement {
    position: [number, number, number];
    target: [number, number, number];
}

/**
 * Build a color buffer from position and intensity data.
 *
 * @param positions - Flat positions [x0,y0,z0, x1,y1,z1, ...].
 * @param intensities - Per-point intensity values.
 * @param count - Number of active points.
 * @param colorMode - "none", "intensity", or "height".
 * @param colors - Pre-allocated output buffer (must be >= count * 3).
 * @param intensityRange - Optional [min, max] override for intensity normalization.
 */
export function buildColorBuffer(
    positions: Float32Array,
    intensities: Float32Array,
    count: number,
    colorMode: ColorMode,
    colors: Float32Array,
    intensityRange?: [number, number]
): void {
    if (colorMode === 'none') return fillNeutral(count, colors);

    const useIntensity = colorMode === 'intensity';
    const [minVal, maxVal] =
        useIntensity && intensityRange
            ? intensityRange
            : valueRange(positions, intensities, count, useIntensity);
    const range = maxVal - minVal;
    const invRange = range === 0 ? 0 : 1 / range;

    for (let i = 0; i < count; i++) {
        const raw = useIntensity ? intensities[i] : positions[i * 3 + 2];
        const t = clamp01((raw - minVal) * invRange);
        turboInto(useIntensity ? Math.sqrt(t) : t, colors, i * 3);
    }
}

/** Neutral gray for every active point. */
function fillNeutral(count: number, colors: Float32Array): void {
    for (let i = 0; i < count; i++) {
        colors[i * 3] = 0.5;
        colors[i * 3 + 1] = 0.5;
        colors[i * 3 + 2] = 0.5;
    }
}

/** The range of whichever value the color mode maps: intensity, or height on the Z axis. */
function valueRange(
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

function clamp01(value: number): number {
    if (value < 0) return 0;
    return value > 1 ? 1 : value;
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
        return { position: [0, -20, 10], target: [0, 0, 0] };
    }

    const center = bounds.getCenter(new Vector3());
    const size = bounds.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 1);
    const distance = maxDim * 1.5;

    // Z is up, as the height color mode also assumes, so the wide offsets go on the ground
    // plane and only a shallow one on the up axis. Offsetting mostly along Z instead would
    // look straight down at the cloud. The negative Y puts the viewer behind and to one
    // side of a forward-facing sensor rather than in front of it.
    return {
        position: [center.x + distance, center.y - distance, center.z + distance * 0.65],
        target: [center.x, center.y, center.z]
    };
}
