import { describe, expect, it } from 'vitest';
import { createPointCloudFrame } from './index';
import { createCameraFixture, createFrameInput } from './fixtures';

describe('camera and source metadata', () => {
    it('rejects calibration in a different frame and invalid projection geometry', () => {
        const camera = createCameraFixture();
        const calibration = camera.calibration!;
        const invalid = [
            { ...calibration, pointCloudCoordinateFrameId: 'CABIN' },
            { ...calibration, rotation: [0, 0, 0, 2] as const },
            { ...calibration, translation: [NaN, 0, 0] as const },
            { ...calibration, intrinsics: { ...calibration.intrinsics, fx: 0 } }
        ];
        invalid.forEach((calibration) => {
            expect(() =>
                createPointCloudFrame({
                    ...createFrameInput(),
                    cameras: [{ ...camera, calibration }]
                })
            ).toThrow();
        });
    });

    it('allows independently missing imagery and calibration', () => {
        const camera = createCameraFixture();
        const frame = createPointCloudFrame({
            ...createFrameInput(),
            cameras: [
                { ...camera, image: null },
                { ...camera, id: 'camera-1', calibration: null }
            ]
        });
        expect(frame.cameras[0].calibration).not.toBeNull();
        expect(frame.cameras[1].image).not.toBeNull();
    });

    it('rejects invalid timestamps and missing stream identity', () => {
        const input = createFrameInput();
        expect(() =>
            createPointCloudFrame({
                ...input,
                timestamp: { ...input.timestamp, nanoseconds: '1.5' }
            })
        ).toThrow();
        expect(() =>
            createPointCloudFrame({
                ...input,
                source: { ...input.source, streamId: '' }
            })
        ).toThrow();
        expect(() =>
            createPointCloudFrame({
                ...input,
                cameras: [{ ...createCameraFixture(), width: 0 }]
            })
        ).toThrow();
    });
});
