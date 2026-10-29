import { get } from 'svelte/store';
import type { EmbeddingRegion } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';

type TabFilters = {
    annotationLabelIds: Set<string>;
    annotationPlotRegion: EmbeddingRegion | null;
};

// Filters of the collections the user left. In memory only, so they last for the session.
const filtersByCollection = new Map<string, TabFilters>();

/**
 * Keeps the filters that live in collection-independent stores per tab.
 *
 * The images and annotations tabs are separate collections. Tags, metadata, dimensions and
 * annotation sources remember their filter per collection themselves. The class filter and the
 * annotation embedding plot selection are single stores, so this puts the left tab's values
 * away and gives the entered tab its own back.
 */
export function useTabFilters() {
    const { selectedAnnotationFilterIds } = useGlobalStorage();
    const { annotationPlotRegion } = useAnnotationPlotSelection();

    const switchTabFilters = (fromCollectionId: string, toCollectionId: string) => {
        filtersByCollection.set(fromCollectionId, {
            annotationLabelIds: new Set(get(selectedAnnotationFilterIds)),
            annotationPlotRegion: get(annotationPlotRegion)
        });
        const saved = filtersByCollection.get(toCollectionId);
        selectedAnnotationFilterIds.set(new Set(saved?.annotationLabelIds));
        annotationPlotRegion.set(saved?.annotationPlotRegion ?? null);
    };

    return { switchTabFilters };
}
