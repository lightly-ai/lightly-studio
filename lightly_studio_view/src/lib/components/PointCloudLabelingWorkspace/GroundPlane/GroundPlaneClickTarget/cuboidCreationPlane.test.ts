import { describe, expect, it } from 'vitest';
import { Euler, Plane, Ray, Vector3 } from 'three';
import { getCuboidCreationPlane } from './cuboidCreationPlane';

const bounds = { min: [-10, -20, 0] as const, max: [30, 40, 12] as const };

describe('cuboid creation planes', () => {
    it.each([
        ['top', new Vector3(0, 0, 1)],
        ['side', new Vector3(1, 0, 0)],
        ['front', new Vector3(0, -1, 0)]
    ] as const)('accepts a click ray from the %s projection', (mode, direction) => {
        const layout = getCuboidCreationPlane(bounds, mode)!;
        const center = new Vector3(...layout.center);
        const normal = new Vector3(0, 0, 1).applyEuler(new Euler(...layout.rotation));
        const plane = new Plane().setFromNormalAndCoplanarPoint(normal, center);
        const ray = new Ray(
            center.clone().addScaledVector(direction, 100),
            direction.clone().negate()
        );
        const hit = ray.intersectPlane(plane, new Vector3());
        expect(hit).not.toBeNull();
        expect(hit!.distanceTo(center)).toBeCloseTo(0);
        if (mode === 'top') expect(center.z).toBeLessThan(bounds.min[2]);
        else expect(center.toArray()).toEqual([10, 10, 6]);
    });

    it('preserves ground placement in perspective and skips an empty scene', () => {
        expect(getCuboidCreationPlane(bounds, 'perspective')).toEqual(
            getCuboidCreationPlane(bounds, 'top')
        );
        expect(getCuboidCreationPlane({ min: [0, 0, 0], max: [0, 0, 0] }, 'side')).toBeNull();
    });
});
