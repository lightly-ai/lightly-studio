import { describe, expect, it } from 'vitest';
import { Vector3 } from 'three';
import { computeDragPlane } from './cuboidFaceDrag';

describe('computeDragPlane', () => {
    const startPoint = new Vector3(0, 0, 0);

    it('returns a plane whose normal is perpendicular to the face normal', () => {
        const plane = computeDragPlane({
            cameraDirection: new Vector3(0, -1, -1).normalize(),
            faceNormal: new Vector3(0, 0, 1),
            startPoint
        });
        expect(Math.abs(plane.normal.dot(new Vector3(0, 0, 1)))).toBeLessThan(1e-6);
    });

    it('preserves the camera direction when it is already perpendicular to face normal', () => {
        const cameraDirection = new Vector3(0, 0, -1);
        const plane = computeDragPlane({
            cameraDirection,
            faceNormal: new Vector3(1, 0, 0),
            startPoint
        });
        expect(plane.normal.x).toBeCloseTo(cameraDirection.x);
        expect(plane.normal.y).toBeCloseTo(cameraDirection.y);
        expect(plane.normal.z).toBeCloseTo(cameraDirection.z);
    });

    it('falls back to camera-facing plane when camera looks along the face normal', () => {
        const cameraDirection = new Vector3(0, 0, -1);
        const plane = computeDragPlane({
            cameraDirection,
            faceNormal: new Vector3(0, 0, 1),
            startPoint
        });
        expect(plane.normal.x).toBeCloseTo(cameraDirection.x);
        expect(plane.normal.y).toBeCloseTo(cameraDirection.y);
        expect(plane.normal.z).toBeCloseTo(cameraDirection.z);
    });

    it('passes through the start point', () => {
        const sp = new Vector3(3, 5, 7);
        const plane = computeDragPlane({
            cameraDirection: new Vector3(1, -1, 0).normalize(),
            faceNormal: new Vector3(0, 1, 0),
            startPoint: sp
        });
        expect(Math.abs(plane.distanceToPoint(sp))).toBeLessThan(1e-6);
    });
});
