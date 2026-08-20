import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';

/**
 * Fills the annotation source filter with the sources of the collection on screen.
 *
 * Call this once per collection route. The Annotation Sources menu only renders on the images
 * grid, so seeding from the menu left the selection describing another tab's sources (or, for
 * a single-source collection, never filled at all). Every grid draws its boxes against this
 * one selection, so it has to be filled everywhere the boxes are drawn.
 */
export function useSeedAnnotationSourceFilter(getCollectionId: () => string): void {
    const annotationCollectionsQuery = useAnnotationCollections(() => ({
        collectionId: getCollectionId()
    }));
    const { seedSelectionIfNeeded } = useAnnotationCollectionsFilter();

    $effect(() => {
        const sources = annotationCollectionsQuery.data;
        if (!sources) return;

        seedSelectionIfNeeded(
            getCollectionId(),
            sources.map((source) => ({ id: source.collection_id, name: source.name }))
        );
    });
}
