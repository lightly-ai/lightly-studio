import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';

/** Keeps tracks whose class matches the annotation's class, plus classless tracks. */
export function filterTracksByAnnotationClass(
    tracks: TrackWithClassNameView[],
    annotationClassName: string | null
): TrackWithClassNameView[] {
    if (annotationClassName == null) return tracks;
    return tracks.filter(
        (t) => t.annotation_class_name == null || t.annotation_class_name === annotationClassName
    );
}
