import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { canonicalCoordinateFrame } from './domain';

/** Maps cuboid annotations from a tick response into the point-cloud domain. */
export function tickAnnotationsToCuboids(annotations: Readonly<TickDetailView['annotations']>) {
    return annotations.flatMap((annotation) => {
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
                trackNumber: annotation.object_track_number ?? null,
                parentTrackNumber: annotation.parent_object_track_number ?? null,
                keyframeId: null,
                center: [details.px, details.py, details.pz] as const,
                size: [details.sx, details.sy, details.sz] as const,
                rotation: [details.qx, details.qy, details.qz, details.qw] as const
            }
        ];
    });
}

/** Builds the distinct annotation classes used by the cuboids in a tick response. */
export function tickAnnotationsToClasses(
    annotations: Readonly<TickDetailView['annotations']>,
    getColor: (name: string) => string
) {
    const classes = new Map<string, { id: string; name: string; color: string }>();

    for (const annotation of annotations) {
        const details = annotation.cuboid_3d_details;
        if (!details) continue;

        const name = annotation.annotation_label.annotation_label_name;
        if (!classes.has(name)) classes.set(name, { id: name, name, color: getColor(name) });
    }

    return [...classes.values()];
}
