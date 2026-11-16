import type { PointBatch } from '$lib/components/PointCloudViewer';

/** Concatenates the active points of several batches into one packed batch. */
export function mergePointBatches(batches: PointBatch[]): PointBatch {
    const count = batches.reduce((total, batch) => total + batch.count, 0);
    const positions = new Float32Array(count * 3);
    const intensities = new Float32Array(count);
    const hasColors = batches.every((batch) => batch.count === 0 || batch.colors);
    const colors = hasColors ? new Float32Array(count * 3) : undefined;
    let offset = 0;
    for (const batch of batches) {
        positions.set(batch.positions.subarray(0, batch.count * 3), offset * 3);
        intensities.set(batch.intensities.subarray(0, batch.count), offset);
        if (colors && batch.colors)
            colors.set(batch.colors.subarray(0, batch.count * 3), offset * 3);
        offset += batch.count;
    }
    return { positions, intensities, ...(colors ? { colors } : {}), count };
}
