import { describe, expect, it } from 'vitest';
import {
    BufferGeometry,
    Float32BufferAttribute,
    PerspectiveCamera,
    Points,
    Scene,
    Vector3
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { createOrbitTargetAnchor, findViewDepth } from './orbitTargetAnchor';

type Position = [number, number, number];

function createScene(...points: Position[]) {
    const geometry = new BufferGeometry();
    geometry.setAttribute('position', new Float32BufferAttribute(points.flat(), 3));
    const pointCloud = new Points(geometry);
    const scene = new Scene().add(pointCloud);
    return { scene, pointCloud };
}

function createControls(position: Position, target: Position) {
    const camera = new PerspectiveCamera();
    camera.up.set(0, 0, 1);
    camera.position.set(...position);
    const controls = new OrbitControls(camera);
    controls.target.set(...target);
    controls.update();
    return { camera, controls };
}

describe('findViewDepth', () => {
    it('returns the median depth of the points at the center of the view', () => {
        const { camera } = createControls([0, 0, 10], [0, 0, 0]);
        const { scene } = createScene([0, 0, 8], [0, 0.1, 0], [0.1, 0, 0], [0, 0, 0]);

        expect(findViewDepth(camera, scene)).toBeCloseTo(10);
    });

    it('returns the depth of the nearest object, not of the denser background behind it', () => {
        const { camera } = createControls([0, 0, 10], [0, 0, 0]);
        const strayPoint: Position = [0, 0, 9];
        const object = Array.from({ length: 5 }, (_, i): Position => [0, 0, 5 - i * 0.05]);
        const background = Array.from({ length: 50 }, (_, i): Position => [0, 0, -10 - i * 0.01]);
        const { scene } = createScene(strayPoint, ...object, ...background);

        expect(findViewDepth(camera, scene)).toBeCloseTo(5.1);
    });

    it('ignores points beside the view axis, behind the camera, and beyond the draw range', () => {
        const { camera } = createControls([0, 0, 10], [0, 0, 0]);
        const { scene, pointCloud } = createScene([5, 0, 0], [0, 0, 20], [0, 0, 0]);
        pointCloud.geometry.setDrawRange(0, 2);

        expect(findViewDepth(camera, scene)).toBeUndefined();
    });

    it('reads the points in the frame of a moved point cloud', () => {
        const { camera } = createControls([0, 0, 10], [0, 0, 0]);
        const { scene, pointCloud } = createScene([0, 0, 0]);
        pointCloud.position.set(0, 0, 4);
        scene.updateMatrixWorld();

        expect(findViewDepth(camera, scene)).toBeCloseTo(6);
    });
});

describe('createOrbitTargetAnchor', () => {
    it('moves the orbit target to the viewed points before a gesture and keeps the view', () => {
        const { camera, controls } = createControls([0, -10, 10], [0, 5, -5]);
        const { scene } = createScene([0, 0, 0]);
        const position = camera.position.clone();
        const direction = camera.getWorldDirection(new Vector3());
        createOrbitTargetAnchor(controls, scene);

        controls.dispatchEvent({ type: 'start' });
        controls.update();

        expect(controls.target.distanceTo(new Vector3(0, 0, 0))).toBeCloseTo(0);
        expect(camera.position.distanceTo(position)).toBeCloseTo(0);
        expect(camera.getWorldDirection(new Vector3()).distanceTo(direction)).toBeCloseTo(0);
    });

    it('keeps the orbit target when no point is at the center of the view', () => {
        const { controls } = createControls([0, -10, 10], [0, 5, -5]);
        const { scene } = createScene([50, 0, 0]);
        const { anchor } = createOrbitTargetAnchor(controls, scene);

        anchor();

        expect(controls.target.distanceTo(new Vector3(0, 5, -5))).toBeCloseTo(0);
    });

    it('keeps the orbit target ahead of a camera that is close to the points', () => {
        const { camera, controls } = createControls([0, 0, 0.2], [0, 0, -3]);
        const { scene } = createScene([0, 0, 0]);
        const { anchor } = createOrbitTargetAnchor(controls, scene);

        anchor();

        expect(camera.position.distanceTo(controls.target)).toBeCloseTo(1);
    });

    it('stops moving the orbit target after disposal', () => {
        const { controls } = createControls([0, -10, 10], [0, 5, -5]);
        const { scene } = createScene([0, 0, 0]);
        const { dispose } = createOrbitTargetAnchor(controls, scene);

        dispose();
        controls.dispatchEvent({ type: 'start' });

        expect(controls.target.distanceTo(new Vector3(0, 5, -5))).toBeCloseTo(0);
    });
});
