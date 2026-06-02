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

/**
 * Counts the distinct annotation sources that have at least one visible (not hidden)
 * annotation.
 */
export const countVisibleSources = (
    annotations: AnnotationView[],
    hiddenAnnotationIds: Set<string>
): number => {
    const visibleSourceIds = new Set<string>();
    for (const annotation of annotations) {
        if (!hiddenAnnotationIds.has(annotation.sample_id)) {
            visibleSourceIds.add(annotation.annotation_collection_id);
        }
    }
    return visibleSourceIds.size;
};

/**
 * Whether every annotation in the list is hidden.
 */
export const areAllAnnotationsHidden = (
    annotations: AnnotationView[],
    hiddenAnnotationIds: Set<string>
): boolean =>
    annotations.length > 0 &&
    annotations.every((annotation) => hiddenAnnotationIds.has(annotation.sample_id));

/**
 * Computes the initially hidden annotations when entering the details page:
 * annotations whose source is not selected in the grid's source filter start hidden.
 *
 * The selection is first intersected with this dataset's sources so that a stale
 * selection from another dataset never hides anything.
 * When that intersection is empty (no filter, or a filter that does not apply here),
 * nothing is hidden.
 */
export const computeSeededHiddenIds = (
    annotations: AnnotationView[],
    selectedCollectionIds: string[],
    sources: AnnotationCollectionView[]
): Set<string> => {
    const sourceIds = new Set(sources.map((source) => source.collection_id));
    const applicableSelectedIds = new Set(selectedCollectionIds.filter((id) => sourceIds.has(id)));
    if (applicableSelectedIds.size === 0) return new Set();

    return new Set(
        annotations
            .filter((annotation) => !applicableSelectedIds.has(annotation.annotation_collection_id))
            .map((annotation) => annotation.sample_id)
    );
};
