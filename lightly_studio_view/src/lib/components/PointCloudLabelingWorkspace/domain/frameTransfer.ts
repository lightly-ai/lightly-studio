import type { PointCloudFrame } from './contracts';
import { createPointCloudFrame } from './pointCloudFrame';

/** Structured-cloneable worker payload. Decode directly into this shape in a worker. */
export type PointCloudFrameTransfer = Parameters<typeof createPointCloudFrame>[0];

/** Export disposable buffers; transferring them never detaches a canonical frame's data. */
/** Returns disposable typed-array copies for structured clone or worker transfer. */
export function exportPointCloudFrame(frame: PointCloudFrame): PointCloudFrameTransfer {
    return {
        id: frame.id,
        source: frame.source,
        timestamp: frame.timestamp,
        sourcePointCount: frame.sourcePointCount,
        coordinateFrame: frame.coordinateFrame,
        cameras: frame.cameras,
        positions: frame.positions.copy(),
        intensity: frame.intensity?.copy(),
        color: frame.color?.copy()
    };
}
