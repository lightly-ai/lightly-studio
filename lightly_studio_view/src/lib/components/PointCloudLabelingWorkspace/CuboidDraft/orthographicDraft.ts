import type { CameraMode } from '../domain';
import { getMissingAxis, MIN_CUBOID_EXTENT, type CuboidBox } from './cuboidDraft';

/** Gives a drawn rectangle a depth proportional to its shorter side. */
export function getProportionalCuboid(mode: CameraMode, rectangle: CuboidBox): CuboidBox | null {
    const missingAxis = getMissingAxis(mode);
    const visibleAxes = ([0, 1, 2] as const).filter((axis) => axis !== missingAxis);
    if (visibleAxes.some((axis) => rectangle.size[axis] <= MIN_CUBOID_EXTENT)) return null;
    const center: [number, number, number] = [...rectangle.center];
    const size: [number, number, number] = [...rectangle.size];
    size[missingAxis] = Math.min(...visibleAxes.map((axis) => rectangle.size[axis]));
    if (mode === 'top') center[missingAxis] += size[missingAxis] / 2;
    return { center, size, yaw: 0 };
}
