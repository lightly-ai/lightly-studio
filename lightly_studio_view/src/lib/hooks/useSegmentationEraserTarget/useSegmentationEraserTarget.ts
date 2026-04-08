import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { decodeRLEToBinaryMask } from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';

type Point = { x: number; y: number };

export type EraserTargetResolution = {
    annotation: AnnotationView | null;
    workingMask: Uint8Array | null;
    error?: 'not_found' | 'locked';
};

export function useSegmentationEraserTarget({
    sample,
    collectionId
}: {
    sample: {
        width: number;
        height: number;
        annotations: AnnotationView[];
    };
    collectionId: string;
}) {
    const { context: annotationLabelContext, isAnnotationLocked } = useAnnotationLabelContext();
    const { selectAnnotation } = useAnnotationSelection();

    const isPointInsideSegmentationBounds = (point: Point, annotation: AnnotationView) => {
        const seg = annotation.segmentation_details;
        if (!seg) return false;

        return (
            point.x >= seg.x &&
            point.x <= seg.x + seg.width &&
            point.y >= seg.y &&
            point.y <= seg.y + seg.height
        );
    };

    const getMaskIndexForPoint = (point: Point) => {
        // Convert pointer coordinates to the nearest pixel and clamp to image bounds.
        const x = Math.min(sample.width - 1, Math.max(0, Math.round(point.x)));
        const y = Math.min(sample.height - 1, Math.max(0, Math.round(point.y)));
        return y * sample.width + x;
    };

    const findAnnotationAtPoint = (point: Point) => {
        const maskIndex = getMaskIndexForPoint(point);

        for (let i = sample.annotations.length - 1; i >= 0; i--) {
            const annotation = sample.annotations[i];
            const segmentationMask = annotation.segmentation_details?.segmentation_mask;
            if (!segmentationMask || !isPointInsideSegmentationBounds(point, annotation)) {
                continue;
            }

            const mask = decodeRLEToBinaryMask(segmentationMask, sample.width, sample.height);
            if (mask[maskIndex] === 1) {
                return annotation;
            }
        }

        return null;
    };

    const isLockedAnnotation = (annotation: AnnotationView | null) =>
        Boolean(annotation && isAnnotationLocked?.(annotation.sample_id));

    const selectAnnotationForErase = (annotation: AnnotationView) => {
        if (annotationLabelContext.annotationId === annotation.sample_id) return;

        selectAnnotation({
            annotationId: annotation.sample_id,
            annotations: sample.annotations,
            collectionId
        });
    };

    const resolveTargetAtPoint = (point: Point): EraserTargetResolution => {
        const annotation = findAnnotationAtPoint(point);
        if (!annotation) {
            return {
                annotation: null,
                workingMask: null,
                error: 'not_found'
            };
        }

        if (isLockedAnnotation(annotation)) {
            return {
                annotation: null,
                workingMask: null,
                error: 'locked'
            };
        }

        const segmentationMask = annotation.segmentation_details?.segmentation_mask;
        if (!segmentationMask) {
            return {
                annotation: null,
                workingMask: null,
                error: 'not_found'
            };
        }

        selectAnnotationForErase(annotation);

        return {
            annotation,
            workingMask: decodeRLEToBinaryMask(segmentationMask, sample.width, sample.height)
        };
    };

    return {
        isLockedAnnotation,
        resolveTargetAtPoint
    };
}
