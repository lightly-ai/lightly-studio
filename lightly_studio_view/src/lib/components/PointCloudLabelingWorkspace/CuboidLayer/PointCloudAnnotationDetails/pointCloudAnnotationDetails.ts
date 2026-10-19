import { Euler, Quaternion } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

type AnnotationDetailsAnnotation = Pick<
    CuboidAnnotation,
    'center' | 'size' | 'rotation' | 'trackNumber'
>;

/**
 * Extracts per-axis Euler angles in degrees (ZYX order) from a unit quaternion.
 *
 * Returns the same x/y/z components that the annotation detail panel displays.
 * Use {@link eulerDegreesToQuaternion} to convert back.
 */
export function rotationToEulerDegrees(
    rotation: CuboidAnnotation['rotation']
): readonly [number, number, number] {
    const [qx, qy, qz, qw] = rotation;
    const euler = new Euler().setFromQuaternion(new Quaternion(qx, qy, qz, qw), 'ZYX');
    const toDeg = (rad: number) => (rad * 180) / Math.PI;
    return [toDeg(euler.x), toDeg(euler.y), toDeg(euler.z)];
}

/**
 * Converts per-axis Euler angles in degrees (ZYX order) to a unit quaternion.
 *
 * Inverse of {@link rotationToEulerDegrees}; used when the user edits rotation
 * components in the annotation detail panel.
 */
export function eulerDegreesToQuaternion(
    rxDeg: number,
    ryDeg: number,
    rzDeg: number
): readonly [number, number, number, number] {
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const q = new Quaternion().setFromEuler(
        new Euler(toRad(rxDeg), toRad(ryDeg), toRad(rzDeg), 'ZYX')
    );
    return [q.x, q.y, q.z, q.w];
}

interface AnnotationDetails {
    location: readonly [string, string, string];
    dimensions: readonly [string, string, string];
    rotation: readonly [string, string, string];
    annotationSourceName?: string;
    trackNumber: number | null;
}

interface CreateAnnotationDetailsParams {
    annotation: AnnotationDetailsAnnotation;
    annotationSourceName?: string;
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
    annotation,
    annotationSourceName
}: CreateAnnotationDetailsParams): AnnotationDetails {
    const [x, y, z] = annotation.center;
    const [l, w, h] = annotation.size;
    const [rx, ry, rz] = rotationToEulerDegrees(annotation.rotation);

    return {
        location: [x.toFixed(2), y.toFixed(2), z.toFixed(2)],
        dimensions: [l.toFixed(2), w.toFixed(2), h.toFixed(2)],
        rotation: [rx.toFixed(1), ry.toFixed(1), rz.toFixed(1)],
        annotationSourceName: annotationSourceName?.trim() ? annotationSourceName : undefined,
        trackNumber: annotation.trackNumber
    };
}
