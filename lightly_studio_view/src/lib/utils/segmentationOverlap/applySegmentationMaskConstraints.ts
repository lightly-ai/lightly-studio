import { removeOverlapFromOtherSemanticAnnotations } from './removeOverlapFromOtherSemanticAnnotations';
import { stripLockedPixels } from './stripLockedPixels';
import type { ApplyMaskConstraintsParams } from './types';

/**
 * Applies lock constraints and overlap cleanup to a working segmentation mask.
 */
export const applySegmentationMaskConstraints = async ({
    workingMask,
    ...rest
}: ApplyMaskConstraintsParams) => {
    // Preserve the drawn mask for overlap removal; locked stripping mutates workingMask.
    const maskForOverlap = workingMask.slice();

    stripLockedPixels({
        mask: workingMask,
        lockedAnnotationIds: rest.lockedAnnotationIds,
        annotations: rest.annotations,
        sample: rest.sample
    });

    await removeOverlapFromOtherSemanticAnnotations({
        newMask: maskForOverlap,
        ...rest
    });
};
