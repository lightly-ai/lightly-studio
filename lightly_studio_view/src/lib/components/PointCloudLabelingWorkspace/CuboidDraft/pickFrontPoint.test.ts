import { describe, expect, it } from 'vitest';
import { PerspectiveCamera } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import { pickFrontPoint } from './pickFrontPoint';

const batch = (points: number[][]): PointBatch => ({
    positions: new Float32Array(points.flat()),
    intensities: new Float32Array(points.length),
    count: points.length
});

/** Looks along +Y from (0, -10, 0); pixel (200, 200) of a 400 px viewport is on the Y axis. */
function createCamera() {
    const camera = new PerspectiveCamera(90, 1, 0.1, 100);
    camera.up.set(0, 0, 1);
    camera.position.set(0, -10, 0);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
}

const viewport = { left: 0, top: 0, width: 400, height: 400 };
const centre = { x: 200, y: 200 };

describe('pickFrontPoint', () => {
    it('picks the point nearest to the camera under the pointer', () => {
        const points = batch([
            [0, 5, 0],
            [0, -2, 0],
            [0, 0, 0]
        ]);
        expect(pickFrontPoint(points, createCamera(), viewport, centre)).toEqual([0, -2, 0]);
    });
    it('ignores the points outside the largest pick radius and behind the camera', () => {
        // At 10 m depth, 1 m to the side is 20 px on screen.
        const points = batch([
            [3, 0, 0],
            [0, -20, 0]
        ]);
        expect(pickFrontPoint(points, createCamera(), viewport, centre)).toBeNull();
    });
    it('prefers a point in a smaller pick radius over a point nearer to the camera', () => {
        // (0.2, 0, 0) is 4 px away; (1, -5, 0) is 40 px away and nearer.
        const points = batch([
            [1, -5, 0],
            [0.2, 0, 0]
        ]);
        expect(pickFrontPoint(points, createCamera(), viewport, centre)).toEqual([
            expect.closeTo(0.2),
            0,
            0
        ]);
    });
    it('picks the lowest point in a larger pick radius', () => {
        // Both points are 20 px away; (0.5, -5, 0.5) is nearer.
        const points = batch([
            [0.5, -5, 0.5],
            [1, 0, -1]
        ]);
        expect(pickFrontPoint(points, createCamera(), viewport, centre)).toEqual([1, 0, -1]);
    });
    it('finds a point between lidar rings in a larger pick radius', () => {
        expect(pickFrontPoint(batch([[1, 0, 0]]), createCamera(), viewport, centre)).toEqual([
            1, 0, 0
        ]);
    });
    it('respects the viewport offset', () => {
        const points = batch([[0, 0, 0]]);
        const shifted = { ...viewport, left: 100, top: 50 };
        expect(pickFrontPoint(points, createCamera(), shifted, { x: 300, y: 250 })).toEqual([
            0, 0, 0
        ]);
    });
});
