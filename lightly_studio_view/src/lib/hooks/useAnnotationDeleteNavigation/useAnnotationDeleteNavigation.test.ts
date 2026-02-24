import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAnnotationDeleteNavigation } from './useAnnotationDeleteNavigation';
import { routeHelpers } from '$lib/routes';
import { goto } from '$app/navigation';
import { readable } from 'svelte/store';

vi.mock('$app/navigation', () => ({
    goto: vi.fn()
}));

const adjacentQueryMock = {
    data: null
};

vi.mock('../useAdjacentAnnotations/useAdjacentAnnotations', () => ({
    useAdjacentAnnotations: () => ({
        query: readable(adjacentQueryMock)
    })
}));

const setAnnotationIdMock = vi.fn();
const setStatusMock = vi.fn();

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        setAnnotationId: setAnnotationIdMock
    })
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        setStatus: setStatusMock
    })
}));

describe('useAnnotationDeleteNavigation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('navigates to next annotation when annotationNext exists', () => {
        adjacentQueryMock.data = {
            next_sample_id: 'annotation-2'
        };

        const { gotoNextAnnotation } = useAnnotationDeleteNavigation({
            collectionId: 'collection-1',
            annotationId: 'annotation-1',
            datasetId: 'dataset-1',
            collectionType: 'annotation'
        });

        gotoNextAnnotation();

        expect(routeHelpers.toSampleWithAnnotation).toBeDefined();

        expect(goto).toHaveBeenCalledWith(
            routeHelpers.toSampleWithAnnotation({
                collectionId: 'collection-1',
                sampleId: 'annotation-2',
                annotationId: 'annotation-2',
                datasetId: 'dataset-1',
                collectionType: 'annotation'
            }),
            { invalidateAll: true }
        );

        expect(setStatusMock).toHaveBeenCalledWith('cursor');
        expect(setAnnotationIdMock).toHaveBeenCalledWith(null);
    });

    it('navigates to annotations list when annotationNext does not exist', () => {
        adjacentQueryMock.data = {
            next_sample_id: null
        };

        const { gotoNextAnnotation } = useAnnotationDeleteNavigation({
            collectionId: 'collection-1',
            annotationId: 'annotation-1',
            datasetId: 'dataset-1',
            collectionType: 'annotation'
        });

        gotoNextAnnotation();

        expect(goto).toHaveBeenCalledWith(
            routeHelpers.toAnnotations('dataset-1', 'annotation', 'collection-1')
        );

        expect(setStatusMock).toHaveBeenCalledWith('cursor');
        expect(setAnnotationIdMock).toHaveBeenCalledWith(null);
    });
});
