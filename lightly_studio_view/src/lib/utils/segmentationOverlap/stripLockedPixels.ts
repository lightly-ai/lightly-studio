import { decodeRLEToBinaryMask } from '$lib/components/SampleAnnotation/utils';
import type { StripLockedParams } from './types';

/**
 * Removes pixels in the working mask that collide with locked segmentation masks.
 */
export const stripLockedPixels = ({
    mask,
    lockedAnnotationIds,
    annotations,
    sample
}: StripLockedParams) => {
    if (!lockedAnnotationIds?.size || !annotations?.length) return;

    annotations
        .filter(
            (ann) =>
                lockedAnnotationIds.has(ann.sample_id) &&
                ann.segmentation_details?.segmentation_mask
        )
        .forEach((ann) => {
            const segmentationMask = ann.segmentation_details?.segmentation_mask;
            if (!segmentationMask) return;

            const lockedMask = decodeRLEToBinaryMask(segmentationMask, sample.width, sample.height);

            for (let i = 0; i < mask.length; i++) {
                if (lockedMask[i] === 1 && mask[i] === 1) {
                    mask[i] = 0;
                }
            }
        });
};
