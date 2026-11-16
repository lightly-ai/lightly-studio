import type { PerspectiveCamera, OrthographicCamera } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/** Inputs needed to bind navigation to one camera and viewport. */
export interface SceneCameraNavigationParams {
    /** Currently rendered camera. */
    camera?: PerspectiveCamera | OrthographicCamera;
    /** Orbit controls that supply the movement target. */
    controls?: OrbitControls;
    /** Whether this viewport owns keyboard input. */
    isActive?: () => boolean;
    /** Routes navigation commands to this viewport. */
    navigationId?: symbol;
}
