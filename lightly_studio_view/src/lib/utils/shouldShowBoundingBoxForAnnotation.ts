import type { Annotation } from '$lib/services/types';

export function shouldShowBoundingBoxForAnnotation(
    annotation: Annotation | undefined,
    showBoundingBoxesForSegmentation: boolean
): boolean {
    return (
        annotation?.annotation_type !== 'segmentation_mask' || showBoundingBoxesForSegmentation
    );
}
