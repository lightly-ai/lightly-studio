import { MathUtils, Vector3 } from 'three';
import type { Matrix4 } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/** Steepest view, as the cosine of its angle to the up axis, that still counts as level. */
const LEVEL_VIEW_LIMIT = Math.cos(MathUtils.degToRad(70));

/** Height change of the orbit target that counts as a move made outside of panning. */
const HEIGHT_TOLERANCE = 1e-6;

/** Private OrbitControls member replaced by {@link enableScreenSpacePanning}. */
interface PanUpControls {
    _panUp: (distance: number, objectMatrix: Matrix4) => void;
}

/**
 * Make vertical drags pan along the screen's up axis, whatever the camera orientation.
 *
 * This replaces the private `_panUp` method of OrbitControls, so re-check it when
 * upgrading three. The `screenSpacePanning` option is not used because it moves the
 * orbit target up and down with the scene.
 *
 * Zooming slows down as the camera nears the orbit target, so a target lifted off the
 * ground by a vertical pan would stop the zoom in mid-air. The lift is
 * therefore tracked and undone by sliding the target along the view direction back to
 * its original height. That leaves the view unchanged and is done as soon as the camera
 * looks down or up steeply enough.
 *
 * @returns A function that restores the default panning.
 */
export function enableScreenSpacePanning(controls: OrbitControls): () => void {
    const panControls = controls as unknown as PanUpControls;
    const camera = controls.object;
    const pan = new Vector3();
    const forward = new Vector3();
    let lift = 0;
    let lastHeight = controls.target.dot(camera.up);

    function forgetLiftAfterExternalMove() {
        if (Math.abs(controls.target.dot(camera.up) - lastHeight) > HEIGHT_TOLERANCE) lift = 0;
    }

    function restoreTargetHeight() {
        forgetLiftAfterExternalMove();
        forward.subVectors(controls.target, camera.position);
        const targetDistance = forward.length();
        forward.divideScalar(targetDistance);
        const climb = forward.dot(camera.up);
        const slide = -lift / climb;
        if (lift !== 0 && Math.abs(climb) >= LEVEL_VIEW_LIMIT && targetDistance + slide > 0) {
            controls.target.addScaledVector(forward, slide);
            lift = 0;
        }
        lastHeight = controls.target.dot(camera.up);
    }

    panControls._panUp = (distance, objectMatrix) => {
        forgetLiftAfterExternalMove();
        pan.setFromMatrixColumn(objectMatrix, 1).multiplyScalar(distance);
        camera.position.add(pan);
        controls.target.add(pan);
        lift += pan.dot(camera.up);
        lastHeight = controls.target.dot(camera.up);
        restoreTargetHeight();
    };
    controls.addEventListener('start', restoreTargetHeight);
    return () => {
        controls.removeEventListener('start', restoreTargetHeight);
        delete (panControls as Partial<PanUpControls>)._panUp;
    };
}
