import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { useAnnotationSelection } from './useAnnotationSelection';

const mockSampleDetailsToolbarContext = {
    status: 'cursor' as 'cursor' | 'brush'
};

const mockAnnotationLabelContext = {
    annotationType: null as AnnotationType | null,
    annotationLabel: null as string | null,
    annotationId: null as string | null,
    lastCreatedAnnotationId: 'prev-id' as string | null
};

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        context: mockSampleDetailsToolbarContext,
        setStatus(status: 'cursor' | 'brush') {
            mockSampleDetailsToolbarContext.status = status;
        }
    })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationLabelContext,
        setAnnotationId(id: string | null) {
            mockAnnotationLabelContext.annotationId = id;
        },
        setAnnotationLabel(label: string | null) {
            mockAnnotationLabelContext.annotationLabel = label;
        },
        setAnnotationType(type: AnnotationType | null) {
            mockAnnotationLabelContext.annotationType = type;
        },
        setLastCreatedAnnotationId(id: string | null) {
            mockAnnotationLabelContext.lastCreatedAnnotationId = id;
        }
    })
}));

const updateLastAnnotationLabelMock = vi.fn();

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        updateLastAnnotationLabel: updateLastAnnotationLabelMock
    })
}));

describe('useAnnotationSelection', () => {
    beforeEach(() => {
        mockSampleDetailsToolbarContext.status = 'cursor';

        mockAnnotationLabelContext.annotationType = null;
        mockAnnotationLabelContext.annotationLabel = null;
        mockAnnotationLabelContext.annotationId = null;
        mockAnnotationLabelContext.lastCreatedAnnotationId = 'prev-id';

        updateLastAnnotationLabelMock.mockClear();
    });

    it('selects instance segmentation annotation and enables brush', () => {
        const annotations = [
            {
                sample_id: 'a1',
                annotation_type: AnnotationType.INSTANCE_SEGMENTATION,
                annotation_label: {
                    annotation_label_name: 'Car'
                }
            }
        ];

        const { selectAnnotation } = useAnnotationSelection();

        selectAnnotation({
            annotationId: 'a1',
            collectionId: 'collection-1',
            annotations
        });

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');

        expect(mockAnnotationLabelContext.annotationType).toBe(
            AnnotationType.INSTANCE_SEGMENTATION
        );
        expect(mockAnnotationLabelContext.annotationLabel).toBe('Car');
        expect(mockAnnotationLabelContext.annotationId).toBe('a1');
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();

        expect(updateLastAnnotationLabelMock).toHaveBeenCalledOnce();
        expect(updateLastAnnotationLabelMock).toHaveBeenCalledWith('collection-1', 'Car');
    });

    it('sets cursor for non-instance annotations', () => {
        const annotations = [
            {
                sample_id: 'a2',
                annotation_type: AnnotationType.OBJECT_DETECTION,
                annotation_label: {
                    annotation_label_name: 'Car'
                }
            }
        ];

        const { selectAnnotation } = useAnnotationSelection();

        selectAnnotation({
            annotationId: 'a2',
            collectionId: 'collection-1',
            annotations
        });

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationId).toBe('a2');

        expect(updateLastAnnotationLabelMock).toHaveBeenCalledOnce();
        expect(updateLastAnnotationLabelMock).toHaveBeenCalledWith('collection-1', 'Car');
    });

    it('selects semantic segmentation annotation and enables brush', () => {
        const annotations = [
            {
                sample_id: 'a-sem',
                annotation_type: AnnotationType.SEMANTIC_SEGMENTATION,
                annotation_label: {
                    annotation_label_name: 'Road'
                }
            }
        ];

        const { selectAnnotation } = useAnnotationSelection();

        selectAnnotation({
            annotationId: 'a-sem',
            collectionId: 'collection-1',
            annotations
        });

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockAnnotationLabelContext.annotationType).toBe(
            AnnotationType.SEMANTIC_SEGMENTATION
        );
        expect(mockAnnotationLabelContext.annotationLabel).toBe('Road');
        expect(mockAnnotationLabelContext.annotationId).toBe('a-sem');
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();

        expect(updateLastAnnotationLabelMock).toHaveBeenCalledOnce();
        expect(updateLastAnnotationLabelMock).toHaveBeenCalledWith('collection-1', 'Road');
    });

    it('toggles annotationId when selecting the same annotation twice', () => {
        mockAnnotationLabelContext.annotationId = 'a3';

        const annotations = [
            {
                sample_id: 'a3',
                annotation_type: AnnotationType.OBJECT_DETECTION,
                annotation_label: {
                    annotation_label_name: 'Car'
                }
            }
        ];

        const { selectAnnotation } = useAnnotationSelection();

        selectAnnotation({
            annotationId: 'a3',
            collectionId: 'collection-1',
            annotations
        });

        expect(mockAnnotationLabelContext.annotationId).toBeNull();

        expect(updateLastAnnotationLabelMock).toHaveBeenCalledOnce();
        expect(updateLastAnnotationLabelMock).toHaveBeenCalledWith('collection-1', 'Car');
    });

    it('does nothing if annotation is not found', () => {
        const { selectAnnotation } = useAnnotationSelection();

        selectAnnotation({
            annotationId: 'missing',
            collectionId: 'collection-1',
            annotations: []
        });

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBe('prev-id');
    });
});
