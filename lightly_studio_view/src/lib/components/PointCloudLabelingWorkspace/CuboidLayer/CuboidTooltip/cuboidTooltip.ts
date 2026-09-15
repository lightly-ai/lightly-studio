import { Euler, Quaternion } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

interface CreateCuboidTooltipParams {
    annotation: CuboidAnnotation;
    annotationClassName: string;
}

interface CuboidTooltip {
    annotationClassName: string;
    location: string;
    dimensions: string;
    rotation: string;
    annotationSourceId: string;
    trackId: string | null;
}

/**
 * Formats the details displayed in a cuboid's hover tooltip.
 *
 * @param params - The cuboid and its resolved annotation class name.
 * @returns Display-ready cuboid metadata with fixed precision.
 */
export function createCuboidTooltip({
    annotation,
    annotationClassName
}: CreateCuboidTooltipParams): CuboidTooltip {
    const [x, y, z] = annotation.center;
    const [width, height, depth] = annotation.size;
    const [qx, qy, qz, qw] = annotation.rotation;
    const euler = new Euler().setFromQuaternion(new Quaternion(qx, qy, qz, qw), 'XYZ');
    const toDeg = (rad: number) => ((rad * 180) / Math.PI).toFixed(1);

    return {
        annotationClassName,
        location: `X: ${x.toFixed(2)}  Y: ${y.toFixed(2)}  Z: ${z.toFixed(2)}`,
        dimensions: `${width.toFixed(2)} × ${height.toFixed(2)} × ${depth.toFixed(2)} m`,
        rotation: `rx: ${toDeg(euler.x)}°  ry: ${toDeg(euler.y)}°  rz: ${toDeg(euler.z)}°`,
        annotationSourceId: annotation.annotationSourceId,
        trackId: annotation.trackId
    };
}
