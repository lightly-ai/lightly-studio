import type { AnnotationView } from '$lib/api/lightly_studio_local';

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
