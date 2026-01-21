import { describe, it, expect, vi, beforeEach } from 'vitest';
import { writable } from 'svelte/store';
import { useAnnotationDeleteNavigation } from './useAnnotationDeleteNavigation';
import type { UseAnnotationAdjacentsData } from '../useAnnotationAdjacents/useAnnotationAdjacents';
import { routeHelpers } from '$lib/routes';
import { goto } from '$app/navigation';

vi.mock('$app/navigation', () => ({
    goto: vi.fn()
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
        const annotationAdjacents = writable<UseAnnotationAdjacentsData>({
            annotationNext: {
                parent_sample_id: 'sample-2',
                sample_id: 'annotation-2'
            }
        } as UseAnnotationAdjacentsData);

        const { gotoNextAnnotation } = useAnnotationDeleteNavigation({
            collectionId: 'collection-1',
            annotationIndex: 3,
            annotationAdjacents
        });

        gotoNextAnnotation();

        expect(routeHelpers.toSampleWithAnnotation).toBeDefined();

        expect(goto).toHaveBeenCalledWith(
            routeHelpers.toSampleWithAnnotation({
                collectionId: 'collection-1',
                sampleId: 'sample-2',
                annotationId: 'annotation-2',
                annotationIndex: 4
            }),
            { invalidateAll: true }
        );

        expect(setStatusMock).toHaveBeenCalledWith('cursor');
        expect(setAnnotationIdMock).toHaveBeenCalledWith(null);
    });

    it('navigates to annotations list when annotationNext does not exist', () => {
        const annotationAdjacents = writable<UseAnnotationAdjacentsData>({
            annotationNext: null
        } as UseAnnotationAdjacentsData);

        const { gotoNextAnnotation } = useAnnotationDeleteNavigation({
            collectionId: 'collection-1',
            annotationIndex: 0,
            annotationAdjacents
        });

        gotoNextAnnotation();

        expect(goto).toHaveBeenCalledWith(routeHelpers.toAnnotations('collection-1'));

        expect(setStatusMock).toHaveBeenCalledWith('cursor');
        expect(setAnnotationIdMock).toHaveBeenCalledWith(null);
    });
});
