import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    decodeRLEToBinaryMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import type { RemoveOverlapParams } from './types';

/**
 * Clears pixels from other semantic masks that overlap the new mask,
 * respecting locked annotations and the current segmentation mode.
 */
export const removeOverlapFromOtherSemanticAnnotations = async ({
    newMask,
    skipId,
    lockedAnnotationIds,
    annotations,
    segmentationMode,
    sample,
    collectionId,
    updateAnnotations
}: RemoveOverlapParams) => {
    if (segmentationMode !== 'semantic') return;
    if (!annotations?.length) return;

    const updates: AnnotationUpdateInput[] = [];

    annotations
        .filter((ann) => {
            const isSemantic = ann.annotation_type === 'semantic_segmentation';
            const hasMask = ann.segmentation_details?.segmentation_mask;
            const isSame = ann.sample_id === skipId;
            const isLocked = lockedAnnotationIds?.has(ann.sample_id);
            return isSemantic && hasMask && !isSame && !isLocked;
        })
        .forEach((ann) => {
            const segmentationMask = ann.segmentation_details?.segmentation_mask;
            if (!segmentationMask) return;

            const otherMask = decodeRLEToBinaryMask(segmentationMask, sample.width, sample.height);

            let changed = false;
            for (let i = 0; i < newMask.length; i++) {
                if (newMask[i] === 1 && otherMask[i] === 1) {
                    otherMask[i] = 0;
                    changed = true;
                }
            }

            if (!changed) return;

            const bbox = computeBoundingBoxFromMask(otherMask, sample.width, sample.height);
            updates.push({
                annotation_id: ann.sample_id,
                collection_id: collectionId,
                segmentation_mask: encodeBinaryMaskToRLE(otherMask),
                bounding_box: bbox ?? null
            });
        });

    if (updates.length) {
        await updateAnnotations(updates);
    }
};
