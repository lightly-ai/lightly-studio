import { describe, expect, it } from 'vitest';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import { toPointBatch } from './toPointBatch';

function frame(positions: Float32Array, intensity?: Float32Array) {
    return createPointCloudFrame({
        id: 'frame-1',
        source: { recordingId: 'r', streamId: '7', messageId: 'm', publishedAt: null },
        timestamp: { nanoseconds: '1789000000000000001', clockId: 'log' },
        coordinateFrame: canonicalCoordinateFrame('lidar'),
        sourcePointCount: positions.length / 3,
        positions,
        intensity,
        cameras: []
    });
}

describe('toPointBatch', () => {
    it('carries positions and the point count through unchanged', () => {
        const batch = toPointBatch(frame(new Float32Array([1, 2, 3, 4, 5, 6])));

        expect(batch.positions).toEqual(new Float32Array([1, 2, 3, 4, 5, 6]));
        expect(batch.count).toBe(2);
    });

    it('copies rather than exposing the frame buffers', () => {
        const source = frame(new Float32Array([1, 2, 3]));

        const batch = toPointBatch(source);
        batch.positions[0] = 99;

        expect(source.positions.copy()).toEqual(new Float32Array([1, 2, 3]));
    });

    it('uses the frame intensity when the recording carried one', () => {
        const batch = toPointBatch(
            frame(new Float32Array([1, 2, 3, 4, 5, 6]), new Float32Array([0.25, 0.75]))
        );

        expect(batch.intensities).toEqual(new Float32Array([0.25, 0.75]));
    });

    it('falls back to a flat intensity per point when the frame has none', () => {
        const batch = toPointBatch(frame(new Float32Array([1, 2, 3, 4, 5, 6])));

        expect(batch.intensities).toEqual(new Float32Array([0, 0]));
        expect(batch.intensities.length).toBe(batch.count);
    });

    it('handles an empty frame', () => {
        const batch = toPointBatch(frame(new Float32Array()));

        expect(batch.count).toBe(0);
        expect(batch.intensities.length).toBe(0);
    });
});
