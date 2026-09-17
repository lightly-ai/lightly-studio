import { Euler, Quaternion } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

interface AnnotationDetails {
    location: readonly [string, string, string];
    dimensions: readonly [string, string, string];
    rotation: readonly [string, string, string];
    annotationSourceId: string;
    trackId: string | null;
}

interface CreateAnnotationDetailsParams {
    annotation: CuboidAnnotation;
}

/**
 * Formats the details displayed in the annotation detail panel.
 *
 * Returns per-axis arrays so callers can render each component in its own
 * column. {@link createCuboidTooltip} uses this to produce its flat strings.
 *
 * @param params - The cuboid whose geometry to format.
 * @returns Display-ready annotation data with fixed precision per axis component.
 */
export function createAnnotationDetails({
    annotation
}: CreateAnnotationDetailsParams): AnnotationDetails {
    const [x, y, z] = annotation.center;
    const [w, h, d] = annotation.size;
    const [qx, qy, qz, qw] = annotation.rotation;
    const euler = new Euler().setFromQuaternion(new Quaternion(qx, qy, qz, qw), 'XYZ');
    const toDeg = (rad: number): string => ((rad * 180) / Math.PI).toFixed(1);

    return {
        location: [x.toFixed(2), y.toFixed(2), z.toFixed(2)],
        dimensions: [w.toFixed(2), h.toFixed(2), d.toFixed(2)],
        rotation: [toDeg(euler.x), toDeg(euler.y), toDeg(euler.z)],
        annotationSourceId: annotation.annotationSourceId,
        trackId: annotation.trackId
    };
}
