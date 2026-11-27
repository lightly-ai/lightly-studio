import type { PointBatch } from '$lib/components/PointCloudViewer';
import { mergePointBatches } from './mergePointBatches';

/** Preserves sensor batches and packs their arrays only when a consumer needs them. */
export function createSegmentedPointBatch(segments: readonly PointBatch[]): PointBatch {
    let packed: PointBatch | undefined;
    const getPacked = () => (packed ??= mergePointBatches([...segments]));
    return {
        segments,
        count: segments.reduce((count, batch) => count + batch.count, 0),
        get positions() {
            return getPacked().positions;
        },
        get intensities() {
            return getPacked().intensities;
        },
        get colors() {
            return getPacked().colors;
        }
    };
}
