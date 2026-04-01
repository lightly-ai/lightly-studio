import { removeOverlapFromOtherSegmentationAnnotations } from './removeOverlapFromOtherSegmentationAnnotations';
import { stripLockedPixels } from './stripLockedPixels';
import type { ApplyMaskConstraintsParams, OverriddenSegmentationAnnotations } from './types';

/**
 * Applies lock constraints and overlap cleanup to a working segmentation mask.
 */
export const applySegmentationMaskConstraints = async ({
    workingMask,
    ...rest
}: ApplyMaskConstraintsParams): Promise<OverriddenSegmentationAnnotations> => {
    // Preserve the drawn mask for overlap removal; locked stripping mutates workingMask.
    const maskForOverlap = workingMask.slice();

    stripLockedPixels({
        mask: workingMask,
        lockedAnnotationIds: rest.lockedAnnotationIds,
        annotations: rest.annotations,
        sample: rest.sample
    });

    return removeOverlapFromOtherSegmentationAnnotations({
        newMask: maskForOverlap,
        ...rest
    });
};
