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

    it('moves the target with the camera, so the view direction and distance stay the same', () => {
        const { camera, controls } = createControls([10, 10, 14]);
        const offset = controls.target.clone().sub(camera.position);
        enableScreenSpacePanning(controls);

        panUp(controls, 2, camera);

        expect(controls.target.clone().sub(camera.position).distanceTo(offset)).toBeCloseTo(0);
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
