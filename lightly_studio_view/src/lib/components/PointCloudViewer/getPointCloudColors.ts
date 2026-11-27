import { buildColorBuffer } from './pointCloudUtils';
import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';

interface CachedColors {
    count: number;
    positions: Float32Array;
    intensities: Float32Array;
    sourceColors?: Float32Array;
    mode: ColorMode;
    min?: number;
    max?: number;
    colors: Float32Array;
}

// Batches are immutable snapshots. Weak keys let previous playback frames be collected.
const cache = new WeakMap<PointBatch, CachedColors>();

/** Shares the latest color mapping of a point batch across its scene viewports. */
export function getPointCloudColors(
    batch: PointBatch,
    mode: ColorMode,
    intensityRange?: [number, number]
): Float32Array {
    const previous = cache.get(batch);
    const [min, max] = intensityRange ?? [];
    if (
        previous?.mode === mode &&
        previous.min === min &&
        previous.max === max &&
        previous.count === batch.count &&
        previous.positions === batch.positions &&
        previous.intensities === batch.intensities &&
        previous.sourceColors === batch.colors
    ) {
        return previous.colors;
    }
    const colors = new Float32Array(batch.count * 3);
    buildColorBuffer({
        ...batch,
        colors,
        colorMode: mode,
        intensityRange,
        pointColors: batch.colors
    });
    cache.set(batch, {
        mode,
        min,
        max,
        colors,
        count: batch.count,
        positions: batch.positions,
        intensities: batch.intensities,
        sourceColors: batch.colors
    });
    return colors;
}
