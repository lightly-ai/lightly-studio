import type { AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import type { AnnotationClass, CuboidAnnotation } from './domain';
import { canonicalCoordinateFrame } from './domain';

/** Maps cuboid annotations from a tick response into the point-cloud domain. */
export function tickAnnotationsToCuboids(
    annotations: readonly AnnotationView[]
): CuboidAnnotation[] {
    return annotations.flatMap((annotation): CuboidAnnotation[] => {
        const details = annotation.cuboid_3d_details;
        if (!details) return [];

        return [
            {
                id: annotation.sample_id,
                frameId: details.frame_id,
                coordinateFrame: canonicalCoordinateFrame(details.frame_id),
                annotationClassId: annotation.annotation_label.annotation_label_name,
                annotationSourceId: annotation.annotation_collection_id,
                trackId: annotation.object_track_id ?? null,
                keyframeId: null,
                center: [details.px, details.py, details.pz],
                size: [details.sx, details.sy, details.sz],
                rotation: [details.qx, details.qy, details.qz, details.qw]
            }
        ];
    });
}

/** Builds the distinct annotation classes used by the cuboids in a tick response. */
export function tickAnnotationsToClasses(
    annotations: readonly AnnotationView[],
    getColor: (name: string) => string
): AnnotationClass[] {
    const classes = new Map<string, AnnotationClass>();

    for (const annotation of annotations) {
        const details = annotation.cuboid_3d_details;
        if (!details) continue;

        const name = annotation.annotation_label.annotation_label_name;
        if (!classes.has(name)) classes.set(name, { id: name, name, color: getColor(name) });
    }

    return [...classes.values()];
}
