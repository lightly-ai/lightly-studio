import { describe, expect, it } from 'vitest';
import { PerspectiveCamera, Vector3 } from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { enableScreenSpacePanning } from './screenSpacePanning';

type Position = [number, number, number];

function createControls(position: Position) {
    const camera = new PerspectiveCamera();
    camera.up.set(0, 0, 1);
    camera.position.set(...position);
    camera.lookAt(0, 0, 0);
    camera.updateMatrix();
    const controls = new OrbitControls(camera);
    controls.screenSpacePanning = false;
    return { camera, controls };
}

function panUp(controls: OrbitControls, distance: number, camera: PerspectiveCamera) {
    (controls as unknown as { _panUp: (d: number, m: unknown) => void })._panUp(
        distance,
        camera.matrix
    );
    controls.update();
}

function getViewDirection(camera: PerspectiveCamera) {
    return camera.getWorldDirection(new Vector3());
}

describe('enableScreenSpacePanning', () => {
    it.each([
        { view: 'tilted', position: [10, 10, 14] as Position },
        { view: 'side', position: [10, 0, 0.01] as Position },
        { view: 'top', position: [0, -0.01, 10] as Position }
    ])('moves the camera along the screen up axis in a $view view', ({ position }) => {
        const { camera, controls } = createControls(position);
        const direction = getViewDirection(camera);
        const expected = new Vector3()
            .setFromMatrixColumn(camera.matrix, 1)
            .multiplyScalar(2)
            .add(camera.position);
        enableScreenSpacePanning(controls);

        panUp(controls, 2, camera);

        expect(camera.position.distanceTo(expected)).toBeCloseTo(0);
        expect(getViewDirection(camera).distanceTo(direction)).toBeCloseTo(0);
    });

    it('keeps the target at its height when the view is steep enough', () => {
        const { camera, controls } = createControls([10, 10, 14]);
        enableScreenSpacePanning(controls);

        panUp(controls, 2, camera);

        expect(controls.target.z).toBeCloseTo(0);
    });

    it('lifts the target in a level view and restores its height once the view is steep', () => {
        const { camera, controls } = createControls([10, 0, 0.01]);
        enableScreenSpacePanning(controls);

        panUp(controls, 2, camera);
        expect(controls.target.z).toBeCloseTo(2);

        camera.position.set(10, 0, 12);
        controls.update();
        const position = camera.position.clone();
        const direction = getViewDirection(camera);
        controls.dispatchEvent({ type: 'start' });
        controls.update();

        expect(controls.target.z).toBeCloseTo(0);
        expect(camera.position.distanceTo(position)).toBeCloseTo(0);
        expect(getViewDirection(camera).distanceTo(direction)).toBeCloseTo(0);
    });

    it('keeps a target height that was set from outside', () => {
        const { camera, controls } = createControls([10, 0, 0.01]);
        enableScreenSpacePanning(controls);
        panUp(controls, 2, camera);

        controls.target.set(0, 0, 5);
        camera.position.set(10, 0, 20);
        controls.update();
        controls.dispatchEvent({ type: 'start' });

        expect(controls.target.z).toBeCloseTo(5);
    });

    it('restores ground plane panning on cleanup', () => {
        const { camera, controls } = createControls([10, 10, 14]);
        const restore = enableScreenSpacePanning(controls);

        restore();
        panUp(controls, 2, camera);

        expect(controls.target.z).toBeCloseTo(0);
        expect(controls.target.length()).toBeCloseTo(2);
    });
});
