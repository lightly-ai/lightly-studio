import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { createAnnotationDetails } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/PointCloudAnnotationDetails';

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
 * Delegates to {@link createAnnotationDetails} for the geometry conversion and
 * joins the per-axis arrays into the flat strings the tooltip renders.
 *
 * @param params - The cuboid and its resolved annotation class name.
 * @returns Display-ready cuboid metadata with fixed precision.
 */
export function createCuboidTooltip({
    annotation,
    annotationClassName
}: CreateCuboidTooltipParams): CuboidTooltip {
    const details = createAnnotationDetails({ annotation });
    const [x, y, z] = details.location;
    const [w, h, d] = details.dimensions;
    const [rx, ry, rz] = details.rotation;

    return {
        annotationClassName,
        location: `X: ${x}  Y: ${y}  Z: ${z}`,
        dimensions: `${w} × ${h} × ${d} m`,
        rotation: `rx: ${rx}°  ry: ${ry}°  rz: ${rz}°`,
        annotationSourceId: details.annotationSourceId,
        trackId: details.trackId
    };
}
