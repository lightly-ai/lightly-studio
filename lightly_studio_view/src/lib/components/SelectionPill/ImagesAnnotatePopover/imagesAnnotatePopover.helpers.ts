import type { AnnotationsFilter, ImageFilter } from '$lib/api/lightly_studio_local';
import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';

/**
 * The image filter that counts the classifications of a selection in one annotation source.
 * An ID selection sends its sample IDs; a select-all keeps its snapshot filter.
 */
export function buildSelectionCountsFilter(target: SelectionTarget, sourceId: string): ImageFilter {
    const restrict = (filter?: AnnotationsFilter | null): AnnotationsFilter => ({
        ...(filter ?? {}),
        collection_ids: [sourceId]
    });
    if (target.kind === 'ids') {
        return { sample_filter: { sample_ids: target.ids, annotations_filter: restrict() } };
    }
    const filter = target.filter as ImageFilter;
    return {
        ...filter,
        sample_filter: {
            ...filter.sample_filter,
            annotations_filter: restrict(filter.sample_filter?.annotations_filter)
        }
    };
}

export function formatDeleteConfirm(className: string, count: number, sourceName: string) {
    return `Delete ${className} from ${count} ${count === 1 ? 'image' : 'images'} in ${sourceName}?`;
}

/** The row index a number key 1-9 picks, or null for any other key. */
export function numberKeyIndex(key: string): number | null {
    return /^[1-9]$/.test(key) ? Number(key) - 1 : null;
}
