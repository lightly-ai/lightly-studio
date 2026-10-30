import { describe, expect, it } from 'vitest';
import { Quaternion, Vector3 } from 'three';
import { createAnnotationFixture } from '../domain/fixtures';
import { getAnnotationPointClipping } from './annotationPointClipping';

describe('annotation point clipping', () => {
    it('retains nearby points and removes distant points around a rotated annotation', () => {
        const rotation = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI / 3);
        const annotation = {
            ...createAnnotationFixture(),
            center: [10, -5, 3] as const,
            size: [2, 4, 6] as const,
            rotation: rotation.toArray() as [number, number, number, number]
        };
        const planes = getAnnotationPointClipping('top', annotation);
        const isVisible = (point: Vector3) => {
            point.applyQuaternion(rotation).add(new Vector3(...annotation.center));
            return planes.every((plane) => plane.distanceToPoint(point) >= -1e-10);
        };
        expect(isVisible(new Vector3())).toBe(true);
        for (let axis = 0; axis < 3; axis++) {
            for (const sign of [-1, 1]) {
                const extent = annotation.size[axis] / 2;
                expect(isVisible(new Vector3().setComponent(axis, sign * (extent + 0.4)))).toBe(
                    true
                );
                expect(isVisible(new Vector3().setComponent(axis, sign * (extent + 0.6)))).toBe(
                    false
                );
            }
        }
    });

    it('shows the full cloud in perspective or without a selected annotation', () => {
        expect(getAnnotationPointClipping('perspective', createAnnotationFixture())).toEqual([]);
        expect(getAnnotationPointClipping('top', undefined)).toEqual([]);
    });
});
