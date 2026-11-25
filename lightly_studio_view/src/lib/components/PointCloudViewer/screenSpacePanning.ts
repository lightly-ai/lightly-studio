import { Vector3 } from 'three';
import type { Matrix4 } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/** Private OrbitControls member replaced by {@link enableScreenSpacePanning}. */
interface PanUpControls {
    _panUp: (distance: number, objectMatrix: Matrix4) => void;
}

/**
 * Make vertical drags pan along the screen's up axis, whatever the camera orientation.
 *
 * This replaces the private `_panUp` method of OrbitControls, so re-check it when
 * upgrading three. The `screenSpacePanning` option is not used because it also changes
 * how the controls zoom to the cursor.
 *
 * @returns A function that restores the default panning.
 */
export function enableScreenSpacePanning(controls: OrbitControls): () => void {
    const panControls = controls as unknown as PanUpControls;
    const camera = controls.object;
    const pan = new Vector3();

    panControls._panUp = (distance, objectMatrix) => {
        pan.setFromMatrixColumn(objectMatrix, 1).multiplyScalar(distance);
        camera.position.add(pan);
        controls.target.add(pan);
    };
    return () => {
        delete (panControls as Partial<PanUpControls>)._panUp;
    };
}
