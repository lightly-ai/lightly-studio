/** Overall size factor — same meaning as TransformControls `size`. */
export const HANDLE_SIZE = 0.5;

/** Size factor for orthographic views, where handles need to be larger to grab. */
export const ORTHOGRAPHIC_HANDLE_SIZE = 1;

/**
 * Maps handle-local X and Y axes to the parent-space scale component that stretches them.
 * Derived from the euler rotations in FACE_DEFINITIONS:
 *   axisIndex 0 [0, π/2, 0]:  localX→parentZ(2), localY→parentY(1)
 *   axisIndex 1 [-π/2, 0, 0]: localX→parentX(0), localY→parentZ(2)
 *   axisIndex 2 [0, 0, 0]:    localX→parentX(0), localY→parentY(1)
 */
export const PERP_SCALE_INDICES: readonly [number, number][] = [
    [2, 1],
    [0, 2],
    [0, 1]
];

interface ComputeHandleScaleParams {
    cameraDistance: number;
    /** Camera vertical field of view in degrees. */
    fov: number;
    /** Vertical world span visible through an orthographic camera. */
    orthographicSpan?: number;
    parentScale: [number, number, number];
    axisIndex: 0 | 1 | 2;
}

/**
 * Computes the handle group scale needed to keep the gizmo at a constant
 * screen-space size, compensating for both camera distance and parent scale.
 *
 * The annotation group's scale is modified during a resize drag. Each local
 * axis is compensated individually so the cap and shaft cross-section stay
 * constant in screen space even when the parent is scaled on the perpendicular
 * axes.
 *
 * @returns `[sx, sy, sz]` — scale along the handle's local X, Y, and Z axes.
 */
export function computeHandleScale({
    cameraDistance,
    fov,
    orthographicSpan,
    parentScale,
    axisIndex
}: ComputeHandleScaleParams): [number, number, number] {
    // Cap mirrors TransformControls: prevents handles growing unbounded at extreme distances.
    const eyeDistance =
        orthographicSpan === undefined
            ? Math.min(cameraDistance * Math.tan((Math.PI / 180) * (fov / 2)), 7)
            : orthographicSpan / 4;
    const base =
        eyeDistance * (orthographicSpan === undefined ? HANDLE_SIZE : ORTHOGRAPHIC_HANDLE_SIZE);
    const [xIdx, yIdx] = PERP_SCALE_INDICES[axisIndex];
    const sz = base / (parentScale[axisIndex] > 0 ? parentScale[axisIndex] : 1);
    const sx = base / (parentScale[xIdx] > 0 ? parentScale[xIdx] : 1);
    const sy = base / (parentScale[yIdx] > 0 ? parentScale[yIdx] : 1);
    return [sx, sy, sz];
}
