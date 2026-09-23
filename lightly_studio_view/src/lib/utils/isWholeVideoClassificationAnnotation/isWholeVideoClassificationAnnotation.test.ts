import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { isWholeVideoClassificationAnnotation } from './isWholeVideoClassificationAnnotation';

describe('isWholeVideoClassificationAnnotation', () => {
    test('returns true for classification annotation with no temporal span', () => {
        const annotation = {
            annotation_type: AnnotationType.CLASSIFICATION,
            temporal_span_details: null
        } as AnnotationView;
        expect(isWholeVideoClassificationAnnotation(annotation)).toBe(true);
    });

    test('returns true when temporal_span_details is undefined', () => {
        const annotation = {
            annotation_type: AnnotationType.CLASSIFICATION,
            temporal_span_details: undefined
        } as AnnotationView;
        expect(isWholeVideoClassificationAnnotation(annotation)).toBe(true);
    });

    test('returns false for classification annotation with a temporal span', () => {
        const annotation = {
            annotation_type: AnnotationType.CLASSIFICATION,
            temporal_span_details: { start_time_s: 0, end_time_s: 1 }
        } as AnnotationView;
        expect(isWholeVideoClassificationAnnotation(annotation)).toBe(false);
    });

    test('returns false for object detection annotation with no temporal span', () => {
        const annotation = {
            annotation_type: AnnotationType.OBJECT_DETECTION,
            temporal_span_details: null
        } as AnnotationView;
        expect(isWholeVideoClassificationAnnotation(annotation)).toBe(false);
    });

    test('returns false for segmentation mask annotation with no temporal span', () => {
        const annotation = {
            annotation_type: AnnotationType.SEGMENTATION_MASK,
            temporal_span_details: null
        } as AnnotationView;
        expect(isWholeVideoClassificationAnnotation(annotation)).toBe(false);
    });
});
