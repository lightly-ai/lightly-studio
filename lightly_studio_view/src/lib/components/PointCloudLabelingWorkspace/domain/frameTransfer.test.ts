import { describe, expect, it } from 'vitest';
import { createPointCloudFrame, exportPointCloudFrame } from './index';
import { createCameraFixture, createFrameInput } from './fixtures';

describe('point-cloud worker boundary', () => {
    it('transfers detached buffers without losing metadata or mutating the cached frame', () => {
        const frame = createPointCloudFrame({
            ...createFrameInput(),
            sourcePointCount: 100,
            cameras: [
                { ...createCameraFixture(), image: { kind: 'decoded', resourceId: 'bitmap-0' } }
            ]
        });
        const payload = exportPointCloudFrame(frame);
        const received = structuredClone(payload, {
            transfer: [payload.positions.buffer, payload.intensity!.buffer, payload.color!.buffer]
        });
        expect(payload.positions.byteLength).toBe(0);
        const restored = createPointCloudFrame(received);
        received.positions.fill(99);
        expect(restored.positions.copy()).toEqual(frame.positions.copy());
        expect(restored.source).toEqual(frame.source);
        expect(restored.timestamp).toEqual(frame.timestamp);
        expect(restored.sourcePointCount).toBe(100);
        expect(restored.bounds).toEqual(frame.bounds);
        expect(restored.cameras).toEqual(frame.cameras);
    });

    it('transfers an empty frame with absent optional attributes', () => {
        const frame = createPointCloudFrame({
            ...createFrameInput(0),
            intensity: undefined,
            color: undefined,
            cameras: []
        });
        const restored = createPointCloudFrame(structuredClone(exportPointCloudFrame(frame)));
        expect(restored.bounds).toBeNull();
        expect(restored.intensity).toBeUndefined();
        expect(restored.color).toBeUndefined();
        expect(restored.cameras).toEqual([]);
    });

    it.each([-1, 1.5, 3, Infinity])('rejects invalid source point count %s', (sourcePointCount) => {
        expect(() => createPointCloudFrame({ ...createFrameInput(), sourcePointCount })).toThrow();
    });
});
