import type { AnnotationView } from '$lib/api/lightly_studio_local';
import {
    isObjectDetectionAnnotation,
    isSegmentationAnnotation,
    type Annotation
} from '$lib/services/types';
import type { BoundingBox } from '$lib/types';

export function getBoundingBox(annotation: Annotation): BoundingBox {
    if (isObjectDetectionAnnotation(annotation) || isSegmentationAnnotation(annotation)) {
        const boundingBox = isObjectDetectionAnnotation(annotation)
            ? annotation.object_detection_details
            : annotation.segmentation_details;

        if (!boundingBox) {
            throw new Error('Missing bounding box data for annotation');
        }

        return {
            x: Math.round(boundingBox.x),
            y: Math.round(boundingBox.y),
            width: Math.round(boundingBox.width),
            height: Math.round(boundingBox.height)
        };
    }

    throw new Error(
        `Annotation type is not supported for bounding box extraction: ${annotation.annotation_type}`
    );
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

export const applyBrushToMask = (
    mask: Uint8Array,
    imageWidth: number,
    imageHeight: number,
    path: { x: number; y: number }[],
    radius: number,
    value: 0 | 1
) => {
    const r2 = radius * radius;

    // Apply the brush for each point along the stroke path.
    for (const p of path) {
        // Round brush center to the nearest pixel.
        const cx = Math.round(p.x);
        const cy = Math.round(p.y);

        const minX = Math.max(0, cx - radius);
        const maxX = Math.min(imageWidth - 1, cx + radius);
        const minY = Math.max(0, cy - radius);
        const maxY = Math.min(imageHeight - 1, cy + radius);

        // Iterate only over pixels inside the bounding box.
        for (let y = minY; y <= maxY; y++) {
            for (let x = minX; x <= maxX; x++) {
                const dx = x - cx;
                const dy = y - cy;

                // Check whether the pixel lies inside the circular brush
                // using squared distance from the center.
                if (dx * dx + dy * dy <= r2) {
                    mask[y * imageWidth + x] = value;
                }
            }
        }
    }
};

export const decodeRLEToBinaryMask = (rle: number[], width: number, height: number): Uint8Array => {
    const mask = new Uint8Array(width * height);
    let idx = 0;
    let value = 0;

    for (const count of rle) {
        for (let i = 0; i < count; i++) {
            if (idx < mask.length) {
                mask[idx++] = value;
            }
        }
        value = value === 0 ? 1 : 0;
    }

    return mask;
};

// Convert a binary mask directly to a data URL for fast preview rendering.
// This avoids the RLE encode/decode round-trip during drawing.
export function maskToDataUrl(
    mask: Uint8Array,
    width: number,
    height: number,
    color: { r: number; g: number; b: number; a: number }
): string {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d')!;
    const imageData = ctx.createImageData(width, height);
    const data = imageData.data;

    for (let i = 0; i < mask.length; i++) {
        if (mask[i] === 1) {
            const idx = i * 4;
            data[idx] = color.r;
            data[idx + 1] = color.g;
            data[idx + 2] = color.b;
            data[idx + 3] = color.a;
        }
    }

    ctx.putImageData(imageData, 0, 0);
    return canvas.toDataURL();
}

/**
 * Interpolate points along a line between two points.
 * Uses linear interpolation to ensure continuous brush strokes
 * even when mouse events are spaced far apart.
 */
export const interpolateLineBetweenPoints = (
    from: { x: number; y: number },
    to: { x: number; y: number }
): { x: number; y: number }[] => {
    const points: { x: number; y: number }[] = [];

    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < 1) {
        return [to];
    }

    const steps = Math.ceil(distance / 0.5);
    const stepX = dx / steps;
    const stepY = dy / steps;

    for (let i = 1; i <= steps; i++) {
        points.push({
            x: from.x + stepX * i,
            y: from.y + stepY * i
        });
    }

    return points;
};
