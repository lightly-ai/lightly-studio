import { Box3 } from 'three';
import { createPointCloudBuffer } from './pointCloudBuffer';
import { getPointCloudFrameColors } from './getPointCloudFrameColors';
import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';

interface FrameBuffer {
    buffer: ReturnType<typeof createPointCloudBuffer>;
    colors?: Float32Array;
}

/** Owns GPU geometries for just the sensor batches in the current accumulation window. */
export function createPointCloudFrameBuffers() {
    const frames = new Map<PointBatch, FrameBuffer>();

    function retain(segments: readonly PointBatch[]): void {
        const active = new Set(segments);
        for (const [segment, frame] of frames) {
            if (active.has(segment)) continue;
            frame.buffer.dispose();
            frames.delete(segment);
        }
        for (const segment of segments) {
            if (frames.has(segment)) continue;
            const buffer = createPointCloudBuffer();
            buffer.updatePositions(segment);
            frames.set(segment, { buffer });
        }
    }

    function update(batch: PointBatch, mode: ColorMode, intensityRange?: [number, number]) {
        const segments = batch.segments ?? [batch];
        retain(segments);
        const colors = getPointCloudFrameColors(batch, mode, intensityRange);
        const bounds = new Box3();
        const geometries = segments.map((segment, index) => {
            const frame = frames.get(segment)!;
            if (frame.colors !== colors[index]) {
                frame.buffer.updateColors(segment.count, 'rgb', undefined, colors[index]);
                frame.colors = colors[index];
            }
            if (frame.buffer.geometry.boundingBox) bounds.union(frame.buffer.geometry.boundingBox);
            return frame.buffer.geometry;
        });
        return { geometries, bounds: bounds.isEmpty() ? undefined : bounds };
    }

    return {
        update,
        dispose: () => {
            for (const frame of frames.values()) frame.buffer.dispose();
            frames.clear();
        }
    };
}
