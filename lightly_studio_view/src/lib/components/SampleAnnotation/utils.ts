import type { AnnotationView } from '$lib/api/lightly_studio_local';
import {
    isInstanceSegmentationAnnotation,
    isObjectDetectionAnnotation,
    type Annotation
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

export const getAnnotations = (annotations: AnnotationView[]) => {
    if (annotations === undefined) {
        return [];
    }

    return annotations
        .filter((annotation) => annotation.annotation_type !== 'classification')
        .sort(sortByAnnotationArea);
};

export const getImageCoordsFromMouse = (
    event: MouseEvent,
    interactionRect: SVGRectElement | null,
    width: number,
    height: number
) => {
    if (!interactionRect) return null;

    const rect = interactionRect.getBoundingClientRect();

    return {
        x: ((event.clientX - rect.left) / rect.width) * width,
        y: ((event.clientY - rect.top) / rect.height) * height
    };
};

// Define the bounding box given a segmentation mask.
export const computeBoundingBoxFromMask = (
    mask: Uint8Array,
    imageWidth: number,
    imageHeight: number
): BoundingBox | null => {
    let minX = imageWidth;
    let minY = imageHeight;
    let maxX = -1;
    let maxY = -1;

    for (let y = 0; y < imageHeight; y++) {
        for (let x = 0; x < imageWidth; x++) {
            if (mask[y * imageWidth + x] === 1) {
                minX = Math.min(minX, x);
                minY = Math.min(minY, y);
                maxX = Math.max(maxX, x);
                maxY = Math.max(maxY, y);
            }
        }
    }

    if (maxX < minX || maxY < minY) return null;

    return {
        x: minX,
        y: minY,
        width: maxX - minX + 1,
        height: maxY - minY + 1
    };
};

// Encode the binary mask into a RLE reprensetation.
export const encodeBinaryMaskToRLE = (mask: Uint8Array): number[] => {
    const rle: number[] = [];
    let lastValue = 0; // background
    let count = 0;

    for (let i = 0; i < mask.length; i++) {
        if (mask[i] === lastValue) {
            count++;
        } else {
            rle.push(count);
            count = 1;
            lastValue = mask[i];
        }
    }

    rle.push(count);
    return rle;
};

export const withAlpha = (color: string, alpha: number) =>
    color.replace(/rgba?\(([^)]+)\)/, (_, c) => {
        const [r, g, b] = c.split(',').map(Number);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    });
