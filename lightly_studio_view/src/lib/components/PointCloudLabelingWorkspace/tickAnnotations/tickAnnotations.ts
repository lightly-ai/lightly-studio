import type { AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import {
    canonicalCoordinateFrame,
    createCuboidAnnotation,
    type AnnotationClass,
    type CuboidAnnotation
} from '$lib/components/PointCloudLabelingWorkspace/domain';
import { getColorByLabel, rgbaToHex } from '$lib/utils';

/**
 * Converts the annotations of a tick into the cuboids rendered in the 3D scene.
 *
 * Annotations without cuboid details are skipped, and so are cuboids the domain rejects, e.g.
 * with a non-positive extent, so one malformed label does not hide the rest of the tick.
 *
 * @param annotations - The annotations returned with the tick details.
 * @returns One cuboid per valid 3D cuboid annotation, keyed by the annotation's sample ID.
 */
export function toCuboidAnnotations(annotations: readonly AnnotationView[]): CuboidAnnotation[] {
    return annotations.flatMap((annotation) => {
        const details = annotation.cuboid_3d_details;
        if (!details) return [];
        // Stored quaternions are unit only up to float precision; the domain needs 1e-6.
        const norm = Math.hypot(details.qx, details.qy, details.qz, details.qw);
        try {
            return [
                createCuboidAnnotation({
                    id: annotation.sample_id,
                    frameId: details.frame_id,
                    coordinateFrame: canonicalCoordinateFrame(details.frame_id),
                    annotationClassId: annotation.annotation_label.annotation_label_name,
                    annotationSourceId: annotation.annotation_collection_id,
                    trackId: annotation.object_track_id ?? null,
                    keyframeId: null,
                    center: [details.px, details.py, details.pz],
                    size: [details.sx, details.sy, details.sz],
                    rotation: [
                        details.qx / norm,
                        details.qy / norm,
                        details.qz / norm,
                        details.qw / norm
                    ]
                })
            ];
        } catch {
            return [];
        }
    });
}

/**
 * Builds one annotation class per label name used by the cuboids.
 *
 * Colors come from `getColorByLabel`, so a label has the same color as in the other views.
 *
 * @param cuboids - Cuboids whose `annotationClassId` is the label name.
 * @returns The classes, in order of first use.
 */
export function toAnnotationClasses(cuboids: readonly CuboidAnnotation[]): AnnotationClass[] {
    const names = [...new Set(cuboids.map((cuboid) => cuboid.annotationClassId))];
    return names.map((name) => ({
        id: name,
        name,
        color: rgbaToHex(getColorByLabel(name).color) ?? '#ffffff'
    }));
}
