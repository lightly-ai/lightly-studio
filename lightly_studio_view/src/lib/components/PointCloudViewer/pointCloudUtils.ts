import { Box3, BufferAttribute, Vector3 } from 'three';
import { turboInto } from './colormap';

/** Determines how points are colored. */
export type ColorMode =
    | 'none'
    | 'intensity'
    | 'height'
    | 'distance'
    | 'density'
    | 'height-distance'
    | 'height-density'
    | 'rgb';

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
    fillGradient(params, getGradientMetrics(colorMode));
}

type GradientMetric = 'intensity' | 'height' | 'distance' | 'density';

function getGradientMetrics(mode: ColorMode): GradientMetric[] {
    if (mode === 'height-distance') return ['height', 'distance'];
    if (mode === 'height-density') return ['height', 'density'];
    if (mode === 'intensity') return ['intensity'];
    if (mode === 'distance') return ['distance'];
    if (mode === 'density') return ['density'];
    return ['height'];
}

/** Color points by one or more normalized spatial metrics. */
function fillGradient(params: BuildColorBufferParams, metrics: GradientMetric[]): void {
    const { count, colors } = params;
    const normalizedValues = metrics.map((metric) => {
        const values = getMetricValues(params, metric);
        const [minVal, maxVal] =
            metric === 'intensity' && params.intensityRange
                ? params.intensityRange
                : computeRange((i) => values[i], count);
        const invRange = maxVal === minVal ? 0 : 1 / (maxVal - minVal);
        return values.map((value) => Math.max(0, Math.min(1, (value - minVal) * invRange)));
    });
    for (let i = 0; i < count; i++) {
        const t = normalizedValues.reduce((sum, values) => sum + values[i], 0) / metrics.length;
        turboInto(metrics[0] === 'intensity' ? Math.sqrt(t) : t, colors, i * 3);
    }
}

function getMetricValues(params: BuildColorBufferParams, metric: GradientMetric): Float32Array {
    const { positions, count } = params;
    if (metric === 'intensity') return params.intensities;
    if (metric === 'height') {
        return Float32Array.from({ length: count }, (_, i) => positions[i * 3 + 2]);
    }
    if (metric === 'distance') {
        return Float32Array.from({ length: count }, (_, i) => {
            const offset = i * 3;
            return Math.hypot(positions[offset], positions[offset + 1], positions[offset + 2]);
        });
    }
    return getDensityValues(params);
}

/** Return the number of points in each point's 0.5 m spatial cell. */
function getDensityValues(params: BuildColorBufferParams): Float32Array {
    const { positions, count } = params;
    const cellSize = 0.5;
    const cellFor = (coordinate: number) => Math.floor(coordinate / cellSize);
    const cellKeyAt = (i: number) => {
        const offset = i * 3;
        return `${cellFor(positions[offset])},${cellFor(positions[offset + 1])},${cellFor(positions[offset + 2])}`;
    };
    const counts = new Map<string, number>();
    for (let i = 0; i < count; i++) {
        const key = cellKeyAt(i);
        counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const values = new Float32Array(count);
    for (let i = 0; i < count; i++) {
        values[i] = Math.log1p(counts.get(cellKeyAt(i)) ?? 1);
    }
    return values;
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
