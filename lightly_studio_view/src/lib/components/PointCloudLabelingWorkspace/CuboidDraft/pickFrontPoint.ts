import { Matrix4, type Camera } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { ScreenPoint } from './cuboidDraft';
import { forEachPoint } from './forEachPoint';

/** Pick radii in pixels; the larger ones reach the ground between lidar rings. */
export const PICK_RADII_PX = [6, 12, 24, 48] as const;
const MAX_PICK_RADIUS_PX = PICK_RADII_PX[PICK_RADII_PX.length - 1];

interface Viewport {
    left: number;
    top: number;
    width: number;
    height: number;
}

/**
 * Point from the smallest pick radius that contains one, or null. The first radius gives the
 * point nearest to the camera; a larger one gives the lowest point, usually the ground in a gap.
 */
export function pickFrontPoint(
    batch: PointBatch | undefined,
    camera: Camera,
    viewport: Viewport,
    pointer: ScreenPoint
): Vector3 | null {
    const matrix = new Matrix4()
        .multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse)
        .toArray();
    const pointerNdcX = ((pointer.x - viewport.left) / viewport.width) * 2 - 1;
    const pointerNdcY = 1 - ((pointer.y - viewport.top) / viewport.height) * 2;
    const pxPerNdcX = viewport.width / 2;
    const pxPerNdcY = viewport.height / 2;
    const picks: (Vector3 | null)[] = PICK_RADII_PX.map(() => null);
    const pickScores: number[] = PICK_RADII_PX.map(() => Infinity);
    forEachPoint(batch, (x, y, z) => {
        const w = matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15];
        if (w <= 0) return;
        const ndcX = (matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12]) / w;
        const offsetXPx = (ndcX - pointerNdcX) * pxPerNdcX;
        // Rejects most points before the full projection.
        if (Math.abs(offsetXPx) > MAX_PICK_RADIUS_PX) return;
        const ndcY = (matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13]) / w;
        const offsetYPx = (ndcY - pointerNdcY) * pxPerNdcY;
        const distanceSquared = offsetXPx ** 2 + offsetYPx ** 2;
        const ring = PICK_RADII_PX.findIndex((radius) => distanceSquared <= radius ** 2);
        if (ring < 0) return;
        const depth = (matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14]) / w;
        const score = ring === 0 ? depth : z;
        if (score >= pickScores[ring]) return;
        picks[ring] = [x, y, z];
        pickScores[ring] = score;
    });
    return picks.find((pick) => pick !== null) ?? null;
}
