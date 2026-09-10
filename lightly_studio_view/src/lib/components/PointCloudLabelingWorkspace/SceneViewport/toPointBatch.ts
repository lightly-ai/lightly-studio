import type { PointBatch } from '$lib/components/PointCloudViewer/pointCloudBuffer';
import type { PointCloudFrame } from '../domain';

/**
 * Adapts a canonical point-cloud frame to the viewer's render batch.
 *
 * The frame owns its packed attributes and only hands out copies, so this is where a frame
 * becomes buffers the renderer may keep. Do it once per frame, never per render.
 *
 * Positions stay in the frame's own coordinates: meters, right-handed, Z up. The viewer
 * treats Z as up as well, so no transform belongs here — a renderer with another convention
 * applies its own, leaving the canonical frame alone.
 *
 * @param frame - The decoded frame to render.
 * @returns A batch of positions, intensities and a point count.
 */
export function toPointBatch(frame: PointCloudFrame): PointBatch {
    const positions = frame.positions.copy();
    const count = positions.length / 3;
    return {
        positions,
        // The viewer requires an intensity per point. Frames carry it only when the
        // recording's PointCloud2 layout has an intensity field and the decoder read it;
        // until it does, zeros keep the neutral and height color modes correct and make the
        // intensity mode flat rather than wrong.
        intensities: frame.intensity?.copy() ?? new Float32Array(count),
        count
    };
}
