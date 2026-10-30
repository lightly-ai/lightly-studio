import type { CuboidAnnotation, Quaternion, Vector3 } from './contracts';
import { assertCompatibleCoordinates } from './coordinates';

type CuboidGeometry = Pick<CuboidAnnotation, 'coordinateFrame' | 'center' | 'size' | 'rotation'>;

function interpolateVector(start: Vector3, end: Vector3, fraction: number): Vector3 {
    return [
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
        start[2] + (end[2] - start[2]) * fraction
    ];
}

function interpolateRotation(start: Quaternion, end: Quaternion, fraction: number): Quaternion {
    const dot = start.reduce((sum, value, index) => sum + value * end[index], 0);
    const target = dot < 0 ? end.map((value) => -value) : end;
    const cosine = Math.min(1, Math.abs(dot));
    const angle = Math.acos(cosine);
    const sine = Math.sin(angle);
    const startWeight = sine < 1e-6 ? 1 - fraction : Math.sin((1 - fraction) * angle) / sine;
    const endWeight = sine < 1e-6 ? fraction : Math.sin(fraction * angle) / sine;
    const values: Quaternion = [
        start[0] * startWeight + target[0] * endWeight,
        start[1] * startWeight + target[1] * endWeight,
        start[2] * startWeight + target[2] * endWeight,
        start[3] * startWeight + target[3] * endWeight
    ];
    const length = Math.hypot(...values);
    return [values[0] / length, values[1] / length, values[2] / length, values[3] / length];
}

/** Interpolates two authored cuboids in one coordinate frame. */
export function interpolateCuboidGeometry(
    start: CuboidGeometry,
    end: CuboidGeometry,
    fraction: number
): CuboidGeometry {
    if (!Number.isFinite(fraction) || fraction < 0 || fraction > 1) {
        throw new Error('Interpolation fraction must be between 0 and 1.');
    }
    assertCompatibleCoordinates(start.coordinateFrame, end.coordinateFrame);
    return {
        coordinateFrame: start.coordinateFrame,
        center: interpolateVector(start.center, end.center, fraction),
        size: interpolateVector(start.size, end.size, fraction),
        rotation: interpolateRotation(start.rotation, end.rotation, fraction)
    };
}
