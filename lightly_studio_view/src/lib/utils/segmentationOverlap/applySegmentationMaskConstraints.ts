import { removeOverlapFromOtherSegmentationAnnotations } from './removeOverlapFromOtherSegmentationAnnotations';
import { stripLockedPixels } from './stripLockedPixels';
import type { ApplyMaskConstraintsParams, OverriddenSegmentationAnnotations } from './types';

/**
 * Applies lock constraints and overlap cleanup to a working segmentation mask.
 *
 * Locked pixels are removed from the working mask first. Other annotations are then trimmed
 * only where the remaining mask has pixels, so pixels rejected by a lock never trim them.
 */
export const applySegmentationMaskConstraints = async ({
    workingMask,
    ...rest
}: ApplyMaskConstraintsParams): Promise<OverriddenSegmentationAnnotations> => {
    stripLockedPixels({
        mask: workingMask,
        lockedAnnotationIds: rest.lockedAnnotationIds,
        annotations: rest.annotations,
        sample: rest.sample
    });

    // Nothing to trim with, so skip decoding the other masks.
    if (!workingMask.includes(1)) {
        return [];
    }

    return removeOverlapFromOtherSegmentationAnnotations({
        newMask: workingMask,
        ...rest
    });
};
