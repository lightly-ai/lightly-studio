import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import type { AnnotationType } from '$lib/api/lightly_studio_local/types.gen';

// Shared across the app the same way the label filter is: the sidebar writes it, the grid and
// count queries read it.
const selectedAnnotationTypes = writable<Set<AnnotationType>>(new Set());

interface UseAnnotationTypeFilterReturn {
    selectedAnnotationTypes: Readable<Set<AnnotationType>>;
    /** `undefined` when nothing is selected, so it can be spread into a filter unconditionally. */
    annotationTypes: Readable<AnnotationType[] | undefined>;
    toggleAnnotationType: (type: AnnotationType) => void;
    clearAnnotationTypes: () => void;
}

/**
 * Filter on the annotation *type* (detection / segmentation / classification), alongside the
 * class and tag filters.
 *
 * An empty selection means "every type", not "no types": an unchecked filter group should not
 * empty the grid.
 */
export function useAnnotationTypeFilter(): UseAnnotationTypeFilterReturn {
    const toggleAnnotationType = (type: AnnotationType) => {
        selectedAnnotationTypes.update((current) => {
            const next = new Set(current);
            if (!next.delete(type)) {
                next.add(type);
            }
            return next;
        });
    };

    const clearAnnotationTypes = () => {
        if (get(selectedAnnotationTypes).size === 0) return;
        selectedAnnotationTypes.set(new Set());
    };

    const annotationTypes = derived(selectedAnnotationTypes, ($types) =>
        $types.size > 0 ? Array.from($types) : undefined
    );

    return {
        selectedAnnotationTypes: readonly(selectedAnnotationTypes),
        annotationTypes,
        toggleAnnotationType,
        clearAnnotationTypes
    };
}
