import type { AnnotationsFilter } from '$lib/api/lightly_studio_local';
import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';

/**
 * The annotations filter that matches an annotation selection. An ID selection sends its
 * annotation IDs; a select-all keeps its snapshot filter. Both stay scoped to the annotation
 * source the grid shows, because label_counts does not scope by the path collection.
 */
export function buildSelectionAnnotationsFilter(
    target: SelectionTarget,
    collectionId: string
): AnnotationsFilter {
    if (target.kind === 'ids') {
        return {
            filter_type: 'annotations',
            sample_ids: target.ids,
            collection_ids: [collectionId]
        };
    }
    const filter = target.filter as AnnotationsFilter;
    return {
        ...filter,
        filter_type: 'annotations',
        collection_ids: filter.collection_ids ?? [collectionId]
    };
}
