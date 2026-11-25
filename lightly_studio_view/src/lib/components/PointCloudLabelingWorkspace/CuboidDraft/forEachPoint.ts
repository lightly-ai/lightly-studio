import type { PointBatch } from '$lib/components/PointCloudViewer';

export type PointVisitor = (x: number, y: number, z: number) => void;

/** Calls the visitor for each active point of every segment of the batch. */
export function forEachPoint(batch: PointBatch | undefined, visit: PointVisitor): void {
    for (const { positions, count } of getSegments(batch)) {
        for (let offset = 0; offset < count * 3; offset += 3) {
            visit(positions[offset], positions[offset + 1], positions[offset + 2]);
        }
    }
}

function getSegments(batch: PointBatch | undefined): readonly PointBatch[] {
    if (!batch) return [];
    return batch.segments ?? [batch];
}
