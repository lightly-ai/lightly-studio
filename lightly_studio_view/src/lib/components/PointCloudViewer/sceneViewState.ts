import { OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';

/** Camera-independent target and scale used to synchronize scene viewports. */
export interface SceneViewState {
    /** Shared world-space point around which the cameras pan and zoom. */
    target: readonly [number, number, number];
    /** World units per CSS pixel at the shared camera target. */
    worldUnitsPerPixel: number;
}

/** Drawable viewport dimensions, excluding device pixel ratio. */
interface ViewportSize {
    /** Viewport width in CSS pixels. */
    width: number;
    /** Viewport height in CSS pixels. */
    height: number;
}

/** Measures scene scale without changing annotation or point-cloud geometry. */
export function getCameraWorldUnitsPerPixel(
    camera: PerspectiveCamera | OrthographicCamera,
    target: Vector3,
    viewportHeight: number
): number | undefined {
    if (viewportHeight <= 0) return undefined;
    const visibleHeight =
        camera instanceof OrthographicCamera
            ? (camera.top - camera.bottom) / camera.zoom
            : 2 *
              camera.position.distanceTo(target) *
              Math.tan((camera.getEffectiveFOV() * Math.PI) / 360);
    const scale = visibleHeight / viewportHeight;
    return Number.isFinite(scale) && scale > 0 ? scale : undefined;
}

/** Applies shared scene scale after zooming, panning, or resizing a viewport. */
export function applyCameraViewState(
    camera: PerspectiveCamera | OrthographicCamera,
    target: Vector3,
    state: SceneViewState,
    viewport: ViewportSize
): boolean {
    const { width, height } = viewport;
    if (
        width <= 0 ||
        height <= 0 ||
        !Number.isFinite(state.worldUnitsPerPixel) ||
        state.worldUnitsPerPixel <= 0
    )
        return false;
    const nextTarget = new Vector3(...state.target);
    const currentScale = getCameraWorldUnitsPerPixel(camera, target, height);
    const aspect =
        camera instanceof OrthographicCamera
            ? (camera.right - camera.left) / (camera.top - camera.bottom)
            : camera.aspect;
    if (
        target.distanceToSquared(nextTarget) < 1e-12 &&
        currentScale !== undefined &&
        Math.abs(currentScale / state.worldUnitsPerPixel - 1) < 1e-8 &&
        Math.abs(aspect - width / height) < 1e-8
    )
        return false;
    camera.position.add(nextTarget.clone().sub(target));
    target.copy(nextTarget);
    const visibleHeight = state.worldUnitsPerPixel * height;
    if (camera instanceof OrthographicCamera) {
        camera.top = 1;
        camera.bottom = -1;
        camera.left = -width / height;
        camera.right = width / height;
        camera.zoom = 2 / visibleHeight;
    } else {
        const distance = visibleHeight / (2 * Math.tan((camera.getEffectiveFOV() * Math.PI) / 360));
        const direction = camera.position.clone().sub(target);
        if (direction.lengthSq() === 0) camera.getWorldDirection(direction).negate();
        camera.position.copy(target).add(direction.normalize().multiplyScalar(distance));
        camera.aspect = width / height;
    }
    camera.updateProjectionMatrix();
    return true;
}
