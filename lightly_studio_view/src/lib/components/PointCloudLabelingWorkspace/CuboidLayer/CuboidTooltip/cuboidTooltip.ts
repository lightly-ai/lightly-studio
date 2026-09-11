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
    const yawRadians = Math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz));

    return {
        annotationClassName,
        location: `X: ${x.toFixed(2)}  Y: ${y.toFixed(2)}  Z: ${z.toFixed(2)}`,
        dimensions: `${width.toFixed(2)} × ${height.toFixed(2)} × ${depth.toFixed(2)} m`,
        rotation: `${((yawRadians * 180) / Math.PI).toFixed(1)}°`,
        annotationSourceId: annotation.annotationSourceId,
        trackId: annotation.trackId
    };
}
