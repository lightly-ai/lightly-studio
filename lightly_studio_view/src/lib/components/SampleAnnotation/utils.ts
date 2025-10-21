import {
    isInstanceSegmentationAnnotation,
    isObjectDetectionAnnotation,
    type Annotation,
    type Sample
} from '$lib/services/types';
import type { BoundingBox } from '$lib/types';

export function getBoundingBox(annotation: Annotation): BoundingBox {
    if (isObjectDetectionAnnotation(annotation) || isInstanceSegmentationAnnotation(annotation)) {
        const boundingBox = {
            ...(isObjectDetectionAnnotation(annotation)
                ? annotation.object_detection_details
                : annotation.instance_segmentation_details)
        };
        return {
            x: Math.round(boundingBox.x),
            y: Math.round(boundingBox.y),
            width: Math.round(boundingBox.width),
            height: Math.round(boundingBox.height)
        };
    } else {
        throw new Error(
            `Annotation type is not supported for bounding box extraction: ${annotation.annotation_type}`
        );
    }
}

/*
We do have situations when smaller annotations can be covered by bigger one, 
and not reachable for click.
If we sort them, the last one should be at the end of the list and clickable first.
*/
export const sortByAnnotationArea = (a: Annotation, b: Annotation) => {
    const bbox1 = getBoundingBox(a);
    const bbox2 = getBoundingBox(b);

    const x1 = bbox1.height * bbox1.width;
    const x2 = bbox2.height * bbox2.width;

    return x2 - x1;
};

export const getAnnotations = (sample: Sample) => {
    if (sample.annotations === undefined) {
        return [];
    }

    return sample.annotations
        .filter((annotation) => annotation.annotation_type !== 'classification')
        .sort(sortByAnnotationArea);
};
