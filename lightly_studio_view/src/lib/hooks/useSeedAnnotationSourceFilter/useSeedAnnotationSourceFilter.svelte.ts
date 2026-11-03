import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';

// The last source list seen per collection, to find the sources that disappeared.
const sourceIdsByCollection = new Map<string, string[]>();

/**
 * Fills the annotation source filter with the sources of the collection on screen.
 *
 * Call this once per collection route. The Annotation Sources menu only renders on the images
 * grid, so seeding from the menu left the selection describing another tab's sources (or, for
 * a single-source collection, never filled at all). Every grid draws its boxes against this
 * one selection, so it has to be filled everywhere the boxes are drawn.
 *
 * It also drops the ticked (source, class) pairs of a source that left the list, for example
 * after a delete in Settings, so the grid does not filter on a source that is gone.
 */
export function useSeedAnnotationSourceFilter(getCollectionId: () => string): void {
    const annotationCollectionsQuery = useAnnotationCollections(() => ({
        collectionId: getCollectionId()
    }));
    const { seedSelectionIfNeeded } = useAnnotationCollectionsFilter();

    $effect(() => {
        const sources = annotationCollectionsQuery.data;
        if (!sources) return;

        const collectionId = getCollectionId();
        seedSelectionIfNeeded(
            collectionId,
            sources.map((source) => ({ id: source.collection_id, name: source.name }))
        );

        const sourceIds = sources.map((source) => source.collection_id);
        const { dropSource } = useAnnotationPairFilter(collectionId);
        (sourceIdsByCollection.get(collectionId) ?? [])
            .filter((id) => !sourceIds.includes(id))
            .forEach(dropSource);
        sourceIdsByCollection.set(collectionId, sourceIds);
    });
}
