import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
import { useTabFilters } from './useTabFilters';

describe('useTabFilters', () => {
    it('gives each tab its own class filter and plot selection back', () => {
        const { selectedAnnotationFilterIds, setSelectedAnnotationFilterIds } = useGlobalStorage();
        const { annotationPlotRegion, saveRegion } = useAnnotationPlotSelection();
        const { switchTabFilters } = useTabFilters();
        const region = { polygon: [{ x: 0, y: 0 }] };

        // On the images tab, filter by "deer".
        setSelectedAnnotationFilterIds('deer');

        // The annotations tab starts without filters; filter by "fox" and lasso some points.
        switchTabFilters('images', 'annotations');
        expect(get(selectedAnnotationFilterIds)).toEqual(new Set());
        setSelectedAnnotationFilterIds('fox');
        saveRegion(region);

        switchTabFilters('annotations', 'images');
        expect(get(selectedAnnotationFilterIds)).toEqual(new Set(['deer']));
        expect(get(annotationPlotRegion)).toBeNull();

        switchTabFilters('images', 'annotations');
        expect(get(selectedAnnotationFilterIds)).toEqual(new Set(['fox']));
        expect(get(annotationPlotRegion)).toEqual(region);
    });
});
