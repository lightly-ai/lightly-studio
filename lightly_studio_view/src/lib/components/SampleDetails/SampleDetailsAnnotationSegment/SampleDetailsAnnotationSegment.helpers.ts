import type { AnnotationCollectionView, AnnotationView } from '$lib/api/lightly_studio_local';

export const UNKNOWN_SOURCE_NAME = 'Unknown source';

interface AnnotationSourceGroup {
    id: string;
    name: string;
    annotations: AnnotationView[];
}

/**
 * Groups annotations by their annotation source.
 *
 * Groups are emitted in the order of `sources`. Sources without annotations are
 * skipped. Annotations whose source is not part of `sources` are appended last
 * under a fallback group per source.
 */
export const groupAnnotationsBySource = (
    annotations: AnnotationView[],
    sources: AnnotationCollectionView[]
): AnnotationSourceGroup[] => {
    const annotationsBySourceId = new Map<string, AnnotationView[]>();
    for (const annotation of annotations) {
        const sourceAnnotations = annotationsBySourceId.get(annotation.annotation_collection_id);
        if (sourceAnnotations) {
            sourceAnnotations.push(annotation);
        } else {
            annotationsBySourceId.set(annotation.annotation_collection_id, [annotation]);
        }
    }

    const groups: AnnotationSourceGroup[] = [];
    for (const source of sources) {
        const sourceAnnotations = annotationsBySourceId.get(source.collection_id);
        if (sourceAnnotations) {
            groups.push({
                id: source.collection_id,
                name: source.name,
                annotations: sourceAnnotations
            });
            annotationsBySourceId.delete(source.collection_id);
        }
    }

    for (const [sourceId, sourceAnnotations] of annotationsBySourceId) {
        groups.push({
            id: sourceId,
            name: UNKNOWN_SOURCE_NAME,
            annotations: sourceAnnotations
        });
    }

    return groups;
};
