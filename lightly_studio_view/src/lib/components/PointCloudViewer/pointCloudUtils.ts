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
    if (colorMode === 'none') {
        for (let i = 0; i < count; i++) {
            colors[i * 3] = 0.5;
            colors[i * 3 + 1] = 0.5;
            colors[i * 3 + 2] = 0.5;
        }
        return;
    }

    let minVal: number;
    let maxVal: number;

    const useIntensity = colorMode === 'intensity';
    if (useIntensity && intensityRange) {
        [minVal, maxVal] = intensityRange;
    } else {
        minVal = Infinity;
        maxVal = -Infinity;
        for (let i = 0; i < count; i++) {
            const v = useIntensity ? intensities[i] : positions[i * 3 + 2];
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
        }
    }

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
