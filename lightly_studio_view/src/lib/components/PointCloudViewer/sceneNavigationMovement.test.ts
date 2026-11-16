import { describe, expect, it } from 'vitest';
import { Vector3 } from 'three';
import { rotatePosition } from './sceneNavigationMovement';

describe('rotatePosition', () => {
    it('orbits around the vertical axis through the center and keeps the height', () => {
        const center = new Vector3(1, 2, 3);
        const position = new Vector3(5, 2, 9);
        rotatePosition(position, center, Math.PI / 2);
        expect(position.x).toBeCloseTo(1);
        expect(position.y).toBeCloseTo(6);
        expect(position.z).toBeCloseTo(9);
        expect(center.toArray()).toEqual([1, 2, 3]);
    });
});
