import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

/**
 * Returns true for classification annotations that apply to the whole video
 * (i.e. no temporal span) rather than a specific time range.
 */
export function isWholeVideoClassificationAnnotation(annotation: AnnotationView): boolean {
    return (
        annotation.annotation_type === AnnotationType.CLASSIFICATION &&
        annotation.temporal_span_details == null
    );
}
