import { describe, expect, it } from 'vitest';
import { Euler, Group, Object3D, OrthographicCamera, Quaternion, Vector3 } from 'three';
import { applyRotationDrag, createRotationDrag, getProjectedCuboidRadius } from './rotationRing';
import { computeCuboidVertices } from '../cuboidGeometry';

const canvas = {
    getBoundingClientRect: () => ({ left: 20, top: 30, width: 400, height: 200 })
} as HTMLCanvasElement;

describe('orthographic rotation ring', () => {
    it.each([
        [0, 0, 10],
        [10, 0, 0],
        [0, -10, 0]
    ] as const)('rotates in the view plane at camera (%s, %s, %s)', (x, y, z) => {
        const camera = new OrthographicCamera(-4, 4, 2, -2);
        camera.position.set(x, y, z);
        camera.up.set(0, z ? 1 : 0, z ? 0 : 1);
        camera.lookAt(0, 0, 0);
        camera.updateMatrixWorld();
        const object = new Object3D();
        object.quaternion.setFromEuler(new Euler(0.2, 0.4, 0.7));
        const initial = object.quaternion.clone();
        const axis = camera.getWorldDirection(new Vector3()).negate();
        const drag = createRotationDrag({
            object,
            camera,
            canvas,
            event: { clientX: 300, clientY: 130, pointerId: 1 } as PointerEvent
        });
        expect(applyRotationDrag(drag, { clientX: 220, clientY: 50 } as PointerEvent)).toBe(true);
        const expected = new Quaternion().setFromAxisAngle(axis, Math.PI / 2).multiply(initial);
        expect(object.quaternion.angleTo(expected)).toBeLessThan(1e-6);
        expect(object.position.toArray()).toEqual([0, 0, 0]);
        expect(object.scale.toArray()).toEqual([1, 1, 1]);
    });

    it('keeps the ring outside every projected corner of an inclined cuboid', () => {
        const size = [2, 4, 6] as const;
        const rotation = new Quaternion().setFromEuler(new Euler(0.3, 0.5, 0.7));
        for (const view of [new Vector3(1, 0, 0), new Vector3(0, 1, 0), new Vector3(0, 0, 1)]) {
            const radius = getProjectedCuboidRadius(size, rotation, view);
            const corners = computeCuboidVertices([0, 0, 0], size, [
                rotation.x,
                rotation.y,
                rotation.z,
                rotation.w
            ]);
            for (const corner of corners) {
                const projected = corner.clone().addScaledVector(view, -corner.dot(view));
                expect(projected.length()).toBeLessThanOrEqual(radius + 1e-10);
            }
        }
    });

    it('respects a rotated parent and handles the angular wrap without tilting', () => {
        const parent = new Group();
        parent.quaternion.setFromEuler(new Euler(0.4, 0.3, 0.2));
        const object = new Object3D();
        parent.add(object);
        const camera = new OrthographicCamera(-4, 4, 2, -2);
        camera.position.z = 10;
        camera.lookAt(0, 0, 0);
        const initial = object.getWorldQuaternion(new Quaternion());
        const drag = createRotationDrag({
            object,
            camera,
            canvas,
            event: { clientX: 140, clientY: 129, pointerId: 1 } as PointerEvent
        });
        applyRotationDrag(drag, { clientX: 140, clientY: 131 } as PointerEvent);
        const change = object
            .getWorldQuaternion(new Quaternion())
            .multiply(initial.clone().invert());
        expect(change.x).toBeCloseTo(0);
        expect(change.y).toBeCloseTo(0);
        expect(change.angleTo(new Quaternion())).toBeLessThan(0.03);
    });
});
