import { AnnotationType, type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';

export interface ClassificationTile {
    /** Used as the selection key and for navigation. Equals `parent_sample_id`. */
    sampleId: string;
    /** First classification entry for the sample; provides the parent payload for rendering. */
    representative: AnnotationWithPayloadView;
    /** All classification annotations for this sample, in insertion order. */
    allAnnotations: AnnotationWithPayloadView[];
}

function isClassificationAnnotation(annotation: AnnotationWithPayloadView): boolean {
    return annotation.annotation.annotation_type === AnnotationType.CLASSIFICATION;
}

/**
 * Groups flat classification annotations into one tile per parent sample.
 *
 * This keeps multi-label classification samples from rendering as duplicate grid tiles while
 * preserving the order in which samples first appear in the query response.
 */
export function groupClassificationsBySample(
    annotations: AnnotationWithPayloadView[]
): ClassificationTile[] {
    const tilesBySampleId = new Map<string, ClassificationTile>();

    for (const annotation of annotations) {
        if (!isClassificationAnnotation(annotation)) {
            continue;
        }

        const sampleId = annotation.annotation.parent_sample_id;
        const existingTile = tilesBySampleId.get(sampleId);
        if (existingTile) {
            existingTile.allAnnotations.push(annotation);
            continue;
        }

        tilesBySampleId.set(sampleId, {
            sampleId,
            representative: annotation,
            allAnnotations: [annotation]
        });
    }

    return Array.from(tilesBySampleId.values());
}
